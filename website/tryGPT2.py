from flask import Flask, Blueprint, render_template, request, jsonify, send_file
from transformers import AutoModel, AutoConfig, pipeline
import torch
import matplotlib

matplotlib.use("agg")
import matplotlib.pyplot as plt
import io
import base64
import os

tryGPT2 = Blueprint("tryGPT2", __name__)

# Specify the directory where the static files are stored
# STATIC_DIR = os.path.join(app.root_path, "static")


@tryGPT2.route("/tryGPT2")
def tryModel():
    return render_template("tryModelGPT2.html")


@tryGPT2.route("/tryGPT2/get", methods=["GET", "POST"])  # type: ignore
def chat():
    msg = request.form["msg"]
    new_length = request.form["len"]
    temp = float(request.form["temperature"])
    max_len = int(new_length)
    input = msg
    return get_Chat_response(input, max_len, temp)


@tryGPT2.route("/tryGPT2/graph", methods=["GET", "POST"])
def plot():
    model_name = "gpt2"
    image_path = plot_weight_distribution(model_name)
    return send_file(image_path, mimetype="image/png")


def get_Chat_response(text, max_length=50, temperature=1.0):
    generator = pipeline("text-generation", model="gpt2")
    output = generator(
        text, max_length=max_length, num_return_sequences=1, temperature=temperature
    )
    # formatted = output[21 : len(output) - 3].replace("/", "")
    formatted = output[0]["generated_text"]
    return formatted


def plot_weight_distribution(model_name):
    config = AutoConfig.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name, config=config)

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
