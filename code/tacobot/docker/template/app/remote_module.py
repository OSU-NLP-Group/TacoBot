required_context = ["text"]


def get_required_context():
    return required_context


def handle_message(msg):
    # your remote module should operate on the text or other context information here
    input_text = msg["text"]
    return input_text
