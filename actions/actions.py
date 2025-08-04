import os
from random import choices
import string
from time import sleep
from typing import Any, Dict, List, Text

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

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

# Configure SendGrid
sg_api_key = os.environ.get("SENDGRID_API_KEY")
email_client = None
if sg_api_key:
    email_client = SendGridAPIClient(sg_api_key)

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
def transfer_money(amount: int, recipient: str) -> str:
    """
    Transfer money from the user's account.
    This is a placeholder for the actual transfer logic.
    """
    sleep(5)  # Simulate a delay for the transfer process
    DBOS.logger.info(f"Transfer to {recipient} of {amount} units completed.")
    return "Success"


@DBOS.step()
def send_confirmation_message(amount: int, recipient: str, success: str) -> bool:
    """
    Send a confirmation message to the user after the transfer.
    This is a placeholder for the actual messaging logic.
    """
    DBOS.logger.info(
        f"Sending confirmation message for transfer of {amount} units, status: {success}."
    )
    if email_client:
        message = Mail(
            from_email='demo@dbos.dev',
            to_emails='qian.li@dbos.dev',
            subject='Transfer Confirmation 🚀',
            html_content=f"<p>Your transfer to <strong>{recipient}</strong> of <strong>{amount}</strong> units status was <strong>{success}</strong.</p>"
        )
        email_client.send(message)
        DBOS.logger.info("Confirmation email sent successfully.")
        return True
    else:
        DBOS.logger.info("Email client not configured. Cannot send confirmation message.")
        # In a real application, you might want to raise an exception or handle this case differently
    return False


@DBOS.workflow()
def transfer_funds_workflow(amount: int, recipient: str) -> bool:
    """
    A simple workflow to transfer funds.
    This is a placeholder for the actual transfer logic.
    """
    # First step, transfer money
    transfer_success = transfer_money(amount, recipient)

    # Wait a bit before sending the confirmation message
    DBOS.sleep(15)

    # Then, send a confirmation message
    status = send_confirmation_message(amount, recipient, transfer_success)
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
        wfid = ''.join(choices(string.ascii_lowercase, k=4))

        with SetWorkflowID(wfid):
            handle = DBOS.start_workflow(
                transfer_funds_workflow, transfer_amount, recipient
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
