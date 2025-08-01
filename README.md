# DBOS Rasa Custom Action Demo

This demo shows how to use DBOS in a Rasa Custom Action. Specifically, all you need to do is to install `dbos` and use it in [actions/actions.py](./actions/actions.py)

```python
import os
from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from dbos import DBOS, DBOSConfig

# Initialize DBOS with configuration
config: DBOSConfig = {
    "name": "dbos-rasa-demo",
    "database_url": os.environ.get("DBOS_DATABASE_URL", "postgresql://postgres:dbos@localhost:5432/dbos_rasa_demo"),
}

# Conductor key is optional to connect to DBOS Conductor for managing workflows via the web UI.
conductor_key=os.environ.get("DBOS_CONDUCTOR_KEY", None)

DBOS(config=config, conductor_key=conductor_key)

@DBOS.step()
def check_current_balance() -> int:
    """
    Check if the user has sufficient funds for the transfer.
    This is a simple check that would typically involve querying a database or an external service.
    """
    balance = 1000
    return balance

@DBOS.workflow()
def transfer_money_workflow(amount: int) -> bool:
    """
    A simple workflow to simulate a money transfer.
    """
    # Check the current funds by invoking the step
    current_balance = check_current_balance()    

    if amount <= current_balance:
        return True
    return False

# Start the DBOS instance
DBOS.launch()

class ActionCheckSufficientFunds(Action):
    def name(self) -> Text:
        return "action_check_sufficient_funds"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        transfer_amount = tracker.get_slot("amount")
        # Invoke a DBOS workflow by simply calling the function
        has_sufficient_funds = transfer_money_workflow(transfer_amount)
        return [SlotSet("has_sufficient_funds", has_sufficient_funds)]
```

## Try This Demo!

First, install dependencies. Note: due to some incompatible dependencies between `dbos` and `rasa-pro`, you must follow the order of installation:

```
uv venv --python 3.11
source .venv/bin/activate

uv pip install dbos
# Install rasa-pro later because it requires older versions of several libraries.
uv pip install rasa-pro
# Upgrade websockets to 13.1
uv pip install websockets==13.1

# Put your Rasa Pro license key here
export RASA_PRO_LICENSE=<YOUR_LICENSE_KEY>

# Configure speech services, using Deepgram for ASR and Cartesia for TTS
export DEEPGRAM_API_KEY=<YOUR-DEEPGRAM-KEY>
export CARTESIA_API_KEY=<YOUR-CARTESIA-KEY>
```


Then, run the following command to start a local Postgres database via Docker:

```
export PGPASSWORD=dbos
dbos postgres start
```

Alternatively, if you already have a Postgres database, you can directly set the `DBOS_DATABASE_URL` environment variable:

```
export DBOS_DATABASE_URL=<Your Postgres URL>
```

Finally, run the following commands to start Rasa.
```
rasa train
rasa inspect
```

Once it's successfully launched, you should be able to see this chat interface:

![Rasa inspect](imgs/rasa-intercept.png)

You can see the money transfer workflow. Chat with it to trigger the loading of the custom actions.
You should see `Registered function for 'action_check_sufficient_funds'` if everything goes well:

![dbos-terminal](imgs/dbos-terminal.png)

Visit [DBOS Console](https://console.dbos.dev/) to register your app as a self-hosted app, and then you'll follow the instructions to export a conductor key.

```
export DBOS_CONDUCTOR_KEY=<Your Key>
```

Restart your Rasa server and load the action again. Now you should see the history of all workflows from the DBOS Console:

![dbos-console](imgs/dbos-console.png)