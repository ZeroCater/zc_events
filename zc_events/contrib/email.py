import uuid
import logging
from zc_events.email import generate_email_data


logger = logging.getLogger(__name__)


def send(event_client, from_email=None, to=None, cc=None, bcc=None, reply_to=None, subject=None,
         plaintext_body=None, html_body=None, headers=None, files=None, attachments=None,
         user_id=None, resource_type=None, resource_id=None, unsubscribe_group=None,
         is_transactional=False, wait_for_response=False):
    """Send an email

    Args:
        event_client - an instatiated event client used for message passing.

    Kwargs:
        to - a list of email addresses to send to
        from - a string that will be used in the "from" field
        cc - a list of email addresses which will be copied on the communication
        bcc - a list of email addresses that will be blind copied on the communication
        reply_to - TBD
        subject - The subject line of the email
        plaintext_body - a plaintext email body
        html_body - a html email body
        user_id - TBD
        headers - TBD
        unsubscribe_group - TBD
        attachments - TBD
        files - TBD
        is_transactional - bool to tell the email server if this is a transactional email (default False)
        wait_for_response - bool to wait for a response or not (default False)
    """
    email_uuid = uuid.uuid4()
    msg = '''MICROSERVICE_SEND_EMAIL: Upload email with UUID {}, to {}, from {},
    with attachments {} and files {}'''
    logger.info(msg.format(email_uuid, to, from_email, attachments, files))
    event_data = generate_email_data(email_uuid,
                                     from_email=from_email, to=to, cc=cc, bcc=bcc, reply_to=reply_to, subject=subject,
                                     plaintext_body=plaintext_body, html_body=html_body, headers=headers, files=files,
                                     attachments=attachments, user_id=user_id, resource_type=resource_type,
                                     resource_id=resource_id, unsubscribe_group=unsubscribe_group,
                                     is_transactional=is_transactional)
    if wait_for_response:
        func = event_client.post
    else:
        func = event_client.post_no_wait

    returned = func('send_email', event_data)
    logger.info('MICROSERVICE_SEND_EMAIL: Sent email with UUID {} and data {}'.format(
        email_uuid, event_data
    ))
    return email_uuid, event_data, returned
