# start by pulling the python image
FROM python:3.9.13-slim-buster

# switch working directory
WORKDIR /app

# copy every content from the local file to the image
ADD . /app

# install the dependencies and packages in the requirements file
RUN pip install -r requirements.txt

# Set Timezone
RUN apt update && apt install tzdata -y
ENV TZ="Asia/Singapore"

# Expose ports (HTTP/HTTPS)
EXPOSE 80 
EXPOSE 443

# Setting Persistent data
VOLUME ["/app-data"]
ADD savedChain.bc /app-data/savedChain.bc

ENV PYTHONUNBUFFERED=1

# configure the container to run in an executed manner
ENTRYPOINT [ "python3" ]
CMD ["webapp.py" ]