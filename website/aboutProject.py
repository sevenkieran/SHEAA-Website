from flask import Blueprint, render_template

aboutProject = Blueprint("aboutProject", __name__)


@aboutProject.route("/aboutProject")
def about():
    return render_template("aboutProject.html")
