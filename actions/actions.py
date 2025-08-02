import os
from time import sleep
from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from dbos import DBOS, DBOSConfig, SetWorkflowID

# Initialize DBOS with configuration
config: DBOSConfig = {
    "name": "dbos-rasa-demo",
    "database_url": os.environ.get(
        "DBOS_DATABASE_URL", "postgresql://postgres:dbos@localhost:5432/dbos_rasa_demo"
    ),
}

# Conductor key is optional to connect to DBOS Conductor for managing workflows via the web UI.
conductor_key = os.environ.get("DBOS_CONDUCTOR_KEY", None)

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
def check_balance_workflow(amount: int) -> bool:
    """
    A simple workflow to check if the user has sufficient funds for a transfer.
    """
    # Check the current funds by invoking the step
    current_balance = check_current_balance()

    if amount <= current_balance:
        return True
    return False


@DBOS.step()
def transfer_money(amount: int) -> str:
    """
    Transfer money from the user's account.
    This is a placeholder for the actual transfer logic.
    """
    sleep(5)  # Simulate a delay for the transfer process
    DBOS.logger.info(f"Transfer of {amount} units completed.")
    return "Success"


@DBOS.step()
def send_confirmation_message(amount: int, success: str) -> bool:
    """
    Send a confirmation message to the user after the transfer.
    This is a placeholder for the actual messaging logic.
    """
    DBOS.logger.info(
        f"Sending confirmation message for transfer of {amount} units, status: {success}."
    )
    return True


@DBOS.workflow()
def transfer_funds_workflow(amount: int) -> bool:
    """
    A simple workflow to transfer funds.
    This is a placeholder for the actual transfer logic.
    """
    # First step, transfer money
    transfer_success = transfer_money(amount)

    # Wait a bit before sending the confirmation message
    DBOS.sleep(15)

    # Then, send a confirmation message
    status = send_confirmation_message(amount, transfer_success)
    return status


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
        has_sufficient_funds = check_balance_workflow(transfer_amount)
        return [SlotSet("has_sufficient_funds", has_sufficient_funds)]


class ActionTransferFunds(Action):
    def name(self) -> Text:
        return "action_transfer_funds"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        transfer_amount = tracker.get_slot("amount")
        recipient = tracker.get_slot("recipient")
        # Invoke a DBOS workflow asynchronously
        with SetWorkflowID(recipient):
            handle = DBOS.start_workflow(
                transfer_funds_workflow, amount=transfer_amount
            )

        return [SlotSet("transfer_status", f"started ID: {handle.workflow_id}")]


class ActionCheckTransferStatus(Action):
    def name(self) -> Text:
        return "action_check_transfer_status"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        workflow_id = tracker.get_slot("transfer_workflow_id")
        if not workflow_id:
            dispatcher.utter_message(text="No transfer workflow ID provided.")
            return []

        # Check the status of the workflow
        status = DBOS.get_workflow_status(workflow_id)
        if status is None:
            dispatcher.utter_message(text=f"Workflow {workflow_id} not found.")
        else:
            dispatcher.utter_message(
                text=f"Workflow {workflow_id} status: {status.status}"
            )

        return []
