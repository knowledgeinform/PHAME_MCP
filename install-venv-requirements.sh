#!/bin/sh
# This script exists if you want to run a python virtual environment in lieu of a conda environment 
# It will create a requirements.txt file and invoke pip for those requirments 
#
# Usage: source install-venv-requirments.sh
# To create the environment
# cd <repo location>
# /usr/local/python12 -m venv .env
#
# To activate the venv:
# cd <repo location>
# source .env/bin/activate
#
# Prerequisites for this script are yq and jq
# pip install yq [inside the virtual environment]
# sudo apt install jq
#
# Once the environment is activated, this script will generate the requirements.txt file and install vi pip

# Ensure we're inside a Python virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
  if [ -f ".env/bin/activate" ]; then
    echo "⚙️  No active virtual environment found. Activating .env..."
    # shellcheck disable=SC1091
    source .env/bin/activate
    echo "✅ Activated virtual environment: $VIRTUAL_ENV"
  else
    echo "❌ Error: You are not in a Python virtual environment."
    echo "👉 Please activate one first, e.g.: "
    echo "   /usr/local/python12 -m venv .env [if not created.  .env is ignored in .gitignore]"
    echo "   source .env/bin/activate [to activate]"
    echo "   Note: if you created one in .env, this script will auto activate it"
    exit 1 
  fi
else
  echo "✅ Virtual environment detected: $VIRTUAL_ENV"
fi

echo "Making requirments.txt file"
yq -r '.dependencies[] | select(type == "object") | .pip[]' environment.yml > requirements.txt

echo "Invoking pip with generated requirements.txt file"
pip install -r requirements.txt