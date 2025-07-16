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
