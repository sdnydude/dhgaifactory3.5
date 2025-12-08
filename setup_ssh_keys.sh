#!/bin/bash
# Setup SSH key-based authentication for autonomous deployment

echo "=== Setting up SSH Key Authentication ==="
echo ""

# Check if SSH key exists
if [ ! -f ~/.ssh/id_rsa ]; then
    echo "Generating SSH key pair..."
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
else
    echo "SSH key already exists."
fi

# Copy SSH key to remote server
echo ""
echo "Copying SSH key to 10.0.0.251..."
echo "You'll need to enter your password one last time:"
ssh-copy-id swebber64@10.0.0.251

echo ""
echo "=== Setup Complete ==="
echo "You can now run deployments without entering a password!"
echo ""
echo "Test with: ssh swebber64@10.0.0.251 'echo Success'"
