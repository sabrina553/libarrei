import os
from dotenv import load_dotenv
from models.hardcover.hardcover import Hardcover
from models.hardcover.transport import TransportLayer

# Load the environment variables
load_dotenv()

token = os.getenv("HARDCOVER_TOKEN")

def main():
    # Create a transport_layer instance with the token
    transport_layer = TransportLayer(token)

    # Create a hardcover instance with the transport_layer
    hardcover = Hardcover(transport_layer)

    variable_values = {
        "isbn": ["9781324089025"],
        "hcid": [],
    }

    result = hardcover.search(variable_values)
    print(result)

if __name__ == "__main__":
    main()