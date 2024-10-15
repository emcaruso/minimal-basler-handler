# script dir
SCRIPTPATH="$(
  cd -- "$(dirname "$0")" >/dev/null 2>&1
  pwd -P
)"

cd $SCRIPTPATH
#
# activate or create venv
if [ -d $SCRIPTPATH/env/.venv ]; then
  echo "Environment found. Activating..."
  . ./env/.venv/bin/activate
else
  echo "Environment not found. Creating a new one..."
  python3 -m venv ./env/.venv
  . ./env/.venv/bin/activate
  pip install -r ./env/requirements.txt
fi

execute
cd src
python server.py
