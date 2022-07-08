FROM python:3.9.13-slim-buster

# Setting Home Directory for containers
WORKDIR /app

# Adding files in the current directory to the Home directory for containers
ADD . /app

# Install required Python dependencies
RUN pip install -r requirements.txt

# Set Timezone
RUN apt update && apt install tzdata -y
ENV TZ="Asia/Singapore"

# Expose ports (HTTP/HTTPS)
EXPOSE 80 
EXPOSE 443

# Setting Persistent data
VOLUME ["/server-data"]
ADD savedChain.bc /server-data/savedChain.bc

ENV PYTHONUNBUFFERED=1

# Commands to run at start-up 
CMD ["python3", "bc_server.py"]