# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:3-slim

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    cron \
    && rm -rf /var/lib/apt/lists/*


# Install Chrome browser and dependencies
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list'
RUN apt-get update && apt-get install -y google-chrome-stable


# Install pip requirements
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

WORKDIR /app
COPY . /app

COPY cronjob /etc/cron.d/container_cronjob

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/container_cronjob

# Apply the cron job
RUN crontab /etc/cron.d/container_cronjob

# Create the log file to be able to run tail
RUN touch /var/log/cron.log
# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers


# Run the cron daemon and tail the log file
CMD cron && tail -f /var/log/cron.log