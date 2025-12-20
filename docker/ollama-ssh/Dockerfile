# Lightweight Docker image with SSH + Ollama pre-installed
# Optimized for fast deployment on Vast.ai
FROM ubuntu:22.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install essential packages: SSH server, curl, and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    curl \
    ca-certificates \
    sudo \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Configure SSH
RUN mkdir -p /var/run/sshd \
    && echo "PermitRootLogin yes" >> /etc/ssh/sshd_config \
    && echo "PasswordAuthentication no" >> /etc/ssh/sshd_config \
    && echo "PubkeyAuthentication yes" >> /etc/ssh/sshd_config \
    && mkdir -p /root/.ssh \
    && chmod 700 /root/.ssh

# Create startup script that starts SSH and Ollama
RUN echo '#\!/bin/bash
# Start SSH daemon
/usr/sbin/sshd

# Start Ollama in background
nohup ollama serve > /var/log/ollama.log 2>&1 &

# Keep container running
tail -f /dev/null
' > /start.sh && chmod +x /start.sh

# Expose SSH and Ollama ports
EXPOSE 22 11434

# Default command
CMD ["/start.sh"]
