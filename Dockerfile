# Use Miniconda3 as the base image
FROM continuumio/miniconda3:latest

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y git unzip g++ gcc libgeos++-dev libproj-dev proj-data proj-bin && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the pyproject.toml file and the entire project directory
COPY pyproject.toml .
COPY . /app

# Create a new conda environment
RUN conda create -n myenv python=3.12 -y

# Activate the conda environment
SHELL ["conda", "run", "-n", "myenv", "/bin/bash", "-c"]

# Install conda packages
RUN conda install -c conda-forge xesmf esmpy h5py numcodecs -y

# Install the project and its dependencies
RUN pip install --no-cache-dir -e .

# Expose port 8000 to the outside world
EXPOSE 8000

# Set the default command to run when the container starts
CMD ["conda", "run", "--no-capture-output", "-n", "myenv", "python", "api/main.py"]