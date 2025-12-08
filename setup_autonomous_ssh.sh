#!/bin/bash
# One-time SSH key setup for autonomous deployment

echo "Setting up SSH key authentication to 10.0.0.251..."
echo "You'll need to enter your password ONE LAST TIME"
echo ""

# Copy the SSH key to the remote server
ssh-copy-id -i ~/.ssh/id_ed25519_fafstudios.pub swebber64@10.0.0.251

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SUCCESS! SSH key authentication is now set up."
    echo "I can now run commands autonomously without passwords!"
    echo ""
    echo "Testing connection..."
    ssh swebber64@10.0.0.251 "echo 'Autonomous connection successful!'"
else
    echo ""
    echo "❌ Setup failed. Please check your password and try again."
fi
