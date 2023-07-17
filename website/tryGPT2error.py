from transformers import (
    GPT2LMHeadModel,
    GPT2Tokenizer,
    GPT2Config,
    AutoModel,
    AutoConfig,
    pipeline,
)
from flask import Flask, Blueprint, render_template, request, jsonify, send_file
import torch
import torch.nn as nn
import matplotlib
import numpy

matplotlib.use("agg")
import matplotlib.pyplot as plt
import io
import base64
import os


tryGPT2error = Blueprint("tryGPT2error", __name__)


@tryGPT2error.route("/tryGPT2error")
def tryModel():
    option_values = [
        "attn.weight",
        "fc.weight",
        "proj.weight",
        "attn.bias",
        "fc.bias",
        "proj.bias",
    ]
    return render_template("tryGPT2error.html", option_values=option_values)


@tryGPT2error.route("/tryGPT2error/graph", methods=["GET"])
def plot():
    modified_model = get_modified_model()  # Get the modified model
    image_path = plot_weight_distribution(modified_model)
    return send_file(image_path, mimetype="image/png")


@tryGPT2error.route("/tryGPT2error/get", methods=["GET", "POST"])
def chat():
    msg = request.form["msg"]
    number_parameters = request.form["num_parameters"]
    new_value = request.form["new_value"]
    error_injection_type = request.form["category"]
    dropout_rate = float(request.form["dropout"])
    scale_factor = float(request.form["scale"])

    num_params = int(number_parameters)
    input_message = msg
    new_val = float(new_value)

    if error_injection_type == "Alex":
        modified_text = GPT2ErrorInjector(
            input_message, num_params=num_params, new_val=new_val
        )
        return str(modified_text)
    elif error_injection_type != None:
        return SatrantResponse(
            msg, attack=error_injection_type, sf=scale_factor, p=dropout_rate
        )
    else:
        return "did not work"


@tryGPT2error.route("/tryGPT2error/get_model", methods=["GET", "POST"])
def get_modified_model():
    msg = request.form["msg"]
    number_parameters = request.form["num_parameters"]
    new_value = request.form["new_value"]
    error_injection_type = request.form["category"]
    dropout_rate = float(request.form["dropout"])
    scale_factor = float(request.form["scale"])

    num_params = int(number_parameters)
    input_message = msg
    new_val = float(new_value)
    if error_injection_type == "Alex":
        modified_model = GPT2ErrorInjector(
            input_message, num_params=num_params, new_val=new_val
        )
    elif error_injection_type != None:
        modified_model = SatrantResponse(
            msg, attack=error_injection_type, sf=scale_factor, p=dropout_rate
        )
    else:
        modified_model = None
    return modified_model


# Satrant's Method


def SatrantResponse(prompt, attack, sf=0.3, p=1e-4):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = (
        torch.float32
    )  # Specify the data type you want to retrieve the number of bits for
    bitwidth = torch.finfo(dtype).bits

    def error_map(
        injectee_shape: tuple,
        dtype_bitwidth: int,
        device: torch.device,
        scale_factor=0.1,
        p=1e-10,
    ) -> torch.Tensor:
        with torch.no_grad():
            error_map = (
                2
                * torch.ones(
                    (*injectee_shape, dtype_bitwidth), dtype=torch.int, device=device
                )
            ) ** torch.arange(0, dtype_bitwidth, dtype=torch.int, device=device).flip(
                dims=(-1,)
            ).expand(
                (*injectee_shape, dtype_bitwidth)
            )

            filter = (
                p
                * nn.functional.dropout(
                    torch.ones_like(error_map, dtype=torch.float, device=device),
                    1.0 - p,
                )
            ).int()

            error_map = (filter * error_map * scale_factor).sum(dim=-1).int()

        return error_map

    def error_inject(model, attack, sf, p):
        error_maps = {}

        for param_name, param in model.named_parameters():
            # Options for attacks are here, you can do weights in general bias in general
            # Then you can do specific kinds of weights/biases attn.weights, proj.weights
            if attack in param_name:  # or "bias" in param_name:
                injectee_shape = param.shape

                error_maps[param_name] = error_map(
                    injectee_shape, bitwidth, device, sf, p
                )

                error_fin = error_maps[param_name]

                param.data = (param.data.to(torch.int) ^ error_fin).to(torch.float)

    config = GPT2Config.from_pretrained("gpt2")

    config.gradient_checkpointing = True

    gpt2_model = GPT2LMHeadModel.from_pretrained("gpt2")

    state_dict = gpt2_model.state_dict()  # Get the model's state_dict
    # Create an instance of the modified model
    modified_model = GPT2LMHeadModel.from_pretrained(
        "gpt2", config=config, state_dict=state_dict
    )

    # Create a tokenizer for the model
    tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
    # Move the model to the specified device
    modified_model = modified_model.to(device)
    # Set the modified model to evaluation mode
    modified_model.eval()

    # Error injection needs a model which is gpt2 an attack name as a string sf as a scale factor to reduce errors and p to introduce randomness
    error_inject(modified_model, attack, sf, p)

    input_text = prompt
    input_ids = tokenizer.encode(input_text, return_tensors="pt").to(device)
    with torch.no_grad():
        output = modified_model.generate(
            input_ids, max_length=25, num_return_sequences=1
        )

    # Decode and print the generated text
    generated_text = tokenizer.decode(output[0], skip_special_tokens=True)
    return generated_text


# Alex's Method
def GPT2ErrorInjector(input_message, num_params, new_val):
    def get_parameter_importance(model: nn.Module) -> dict:
        parameter_importance = {}
        for name, parameter in model.named_parameters():
            parameter_importance[name] = torch.std(
                parameter
            ).item()  # Calculate importance based on standard deviation
        return parameter_importance

    def modify_parameters(
        model: nn.Module, num_params: int, modification_func: callable
    ):
        parameter_importance = get_parameter_importance(model)
        sorted_params = sorted(
            parameter_importance.items(), key=lambda x: x[1], reverse=True
        )
        total_params = len(sorted_params)

        if num_params > total_params:
            num_params = total_params

        selected_params = [param[0] for param in sorted_params][:num_params]

        for parameter_name in selected_params:
            parameter = dict(model.named_parameters())[parameter_name]
            modified_parameter = modification_func(parameter)
            dict(model.named_parameters())[parameter_name].data.copy_(
                modified_parameter
            )

    # Create the GPT-2 model and tokenizer
    model = GPT2LMHeadModel.from_pretrained("gpt2")
    tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

    # Specify the number of distinct parameters to modify and the modification function
    modification_func = (
        lambda parameter: parameter.clone().fill_(new_val)
        if torch.rand(1) < 0.5
        else parameter.clone()
    )

    # Modify a specific number of distinct parameters of highest importance
    modify_parameters(model, num_params, modification_func)

    # Set the device to run the model on
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    # Generate text using the modified model
    input_ids = tokenizer.encode(input_message, return_tensors="pt").to(device)
    with torch.no_grad():
        output = model.generate(input_ids, max_length=50, num_return_sequences=1)

    # Decode and print the generated text
    generated_text = tokenizer.decode(output[0], skip_special_tokens=True)
    return generated_text


def plot_weight_distribution(model_name):
    # config = AutoConfig.from_pretrained(model_name)
    model = get_modified_model()

    # Create an empty list to store the parameter values
    parameter_values = []

    # Create an empty tensor to concatenate the parameters
    concatenated_tensor = None

    # Iterate through the named parameters of the model
    for name, param in model.named_parameters():
        if "weight" in name:
            # Reshape the parameter tensor to a 1D tensor
            param_tensor = param.view(-1)

            # Concatenate the parameter tensor to the existing tensor
            if concatenated_tensor is None:
                concatenated_tensor = param_tensor
            else:
                concatenated_tensor = torch.cat((concatenated_tensor, param_tensor))

    # Move the concatenated tensor to the GPU
    if torch.cuda.is_available():
        concatenated_tensor = concatenated_tensor.cuda()

    # Convert the GPU tensor to a CPU tensor (if necessary)
    concatenated_tensor_cpu = concatenated_tensor.cpu()

    # Detach the tensor from the computation graph and convert it to a NumPy array
    parameter_values = concatenated_tensor_cpu.detach().numpy()

    # Plotting the weight distribution
    start = -10.0
    stop = 10.0
    step = 0.05
    bins = [round(start + i * step, 1) for i in range(int((stop - start) / step))]

    plt.hist(parameter_values, bins=bins, edgecolor="black", log=True)

    plt.xlabel("Parameter Values")
    plt.ylabel("Frequency")
    plt.title(f"{model_name} Weight Distribution")

    # Save the weight distribution plot as a file on the server
    # buffer = io.BytesIO()
    # plt.savefig(buffer, format="png")
    # buffer.seek(0)
    # image_path = "static/weight_distribution.png"
    # with open(image_path, "wb") as f:
    #     f.write(buffer.read())
    # Save the weight distribution plot as an image file
    # Create the 'static' directory if it doesn't exist
    static_dir = os.path.join(os.getcwd(), "static")
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)

    # Save the weight distribution plot as an image file
    image_filename = "weight_distribution.png"
    image_path = os.path.join(static_dir, image_filename)
    plt.savefig(image_path)

    return image_path


# def plot_weight_distribution(model):
#     # config = AutoConfig.from_pretrained(model_name)
#     # model = AutoModel.from_pretrained(model_name, config=config)

#     # Create an empty list to store the parameter values
#     parameter_values = []

#     # Create an empty tensor to concatenate the parameters
#     concatenated_tensor = None

#     # Iterate through the named parameters of the model
#     for name, param in model.named_parameters():
#         if "weight" in name:
#             # Reshape the parameter tensor to a 1D tensor
#             param_tensor = param.view(-1)

#             # Concatenate the parameter tensor to the existing tensor
#             if concatenated_tensor is None:
#                 concatenated_tensor = param_tensor
#             else:
#                 concatenated_tensor = torch.cat((concatenated_tensor, param_tensor))

#     # Move the concatenated tensor to the GPU
#     if torch.cuda.is_available():
#         concatenated_tensor = concatenated_tensor.cuda()

#     # Convert the GPU tensor to a CPU tensor (if necessary)
#     concatenated_tensor_cpu = concatenated_tensor.cpu()

#     # Detach the tensor from the computation graph and convert it to a NumPy array
#     parameter_values = concatenated_tensor_cpu.detach().numpy()

#     # Plotting the weight distribution
#     start = -10.0
#     stop = 10.0
#     step = 0.05
#     # bins = [round(start + i * step, 1) for i in range(int((stop - start) / step))]

#     # plt.hist(parameter_values, bins=bins, edgecolor="black", log=True)

#     # plt.xlabel("Parameter Values")
#     # plt.ylabel("Frequency")
#     # plt.title(f"{model_name} Weight Distribution")

#     # Create a histogram of the parameter values
#     plt.figure(figsize=(10, 6))
#     plt.hist(parameter_values, bins=50, edgecolor="black")
#     plt.xlabel("Parameter Value")
#     plt.ylabel("Frequency")
#     plt.title("Weight Distribution")
#     plt.grid(True)

#     # Save the weight distribution plot as a file on the server
#     # buffer = io.BytesIO()
#     # plt.savefig(buffer, format="png")
#     # buffer.seek(0)
#     # image_path = "static/weight_distribution.png"
#     # with open(image_path, "wb") as f:
#     #     f.write(buffer.read())
#     # Save the weight distribution plot as an image file
#     # Create the 'static' directory if it doesn't exist
#     # static_dir = os.path.join(os.getcwd(), "static")
#     # if not os.path.exists(static_dir):
#     #     os.makedirs(static_dir)
#     buf = io.BytesIO()
#     plt.savefig(buf, format="png")
#     buf.seek(0)

#     # Convert the plot buffer to base64 encoding
#     plot_data = base64.b64encode(buf.read()).decode("utf-8")

#     # Close the plot
#     plt.close()

#     # Save the weight distribution plot as an image file
#     image_path = "weight_distribution.png"
#     with open(image_path, "wb") as f:
#         f.write(base64.b64decode(plot_data))

#     return image_path
# image_path = os.path.join(static_dir, image_filename)
# plt.savefig(image_path)

# return image_path


# def GPT2ErrorInjector(input_message, num_params, new_val):
#     def get_parameter_importance(model: nn.Module) -> dict:
#         parameter_importance = {}
#         for name, parameter in model.named_parameters():
#             parameter_importance[name] = torch.std(
#                 parameter
#             ).item()  # Calculate importance based on standard deviation
#         return parameter_importance

#     def modify_parameters(
#         model: nn.Module, num_params: int, modification_func: callable
#     ):
#         parameter_importance = get_parameter_importance(model)
#         sorted_params = sorted(
#             parameter_importance.items(), key=lambda x: x[1], reverse=True
#         )
#         total_params = len(sorted_params)

#         if num_params > total_params:
#             num_params = total_params

#         selected_params = [param[0] for param in sorted_params]
#         modified_params = set()

#         for name, parameter in model.named_parameters():
#             if len(modified_params) < num_params and name in selected_params:
#                 modified_params.add(name)
#                 modified_parameter = modification_func(parameter)
#                 parameter.data.copy_(modified_parameter)
#             else:
#                 parameter.requires_grad_(False)

#     # Create the GPT-2 model and tokenizer
#     model = GPT2LMHeadModel.from_pretrained("gpt2")
#     tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

#     # Specify the number of distinct parameters to modify and the modification function
#     modification_func = lambda parameter: parameter.clone().fill_(
#         new_val
#     )  # Example modification: set the parameter values to 0.0

#     # Modify a specific number of distinct parameters of highest importance
#     modify_parameters(model, num_params, modification_func)

#     # Set the device to run the model on
#     device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
#     model = model.to(device)

#     # Generate text using the modified model
#     input_ids = tokenizer.encode(input_message, return_tensors="pt").to(device)
#     with torch.no_grad():
#         output = model.generate(input_ids, max_length=50, num_return_sequences=1)

#     # Decode and print the generated text
#     generated_text = tokenizer.decode(output[0], skip_special_tokens=True)
#     return generated_text
