import os
from dotenv import load_dotenv

from libarrei.models.hardcover.hardcover import Hardcover
from libarrei.models.hardcover.transport import TransportLayer as TransportLayerHC
from libarrei.models.goodreads.goodreads import Goodreads
from libarrei.models.goodreads.transport import TransportLayer as TransportLayerGR

# Load the environment variables
load_dotenv()
hc_token = os.getenv("HARDCOVER_TOKEN")
gr_token = os.getenv("GOODREADS_TOKEN")

def main():

    # Create a transport_layer instance
    transport_layer_hc = TransportLayerHC(hc_token)
    transport_layer_gr = TransportLayerGR(gr_token)

    # Create instances with the transport_layer
    hardcover = Hardcover(transport_layer_hc)
    goodreads = Goodreads(transport_layer_gr)

    variable_values_hc = {
        "isbn": ["9781324089025"],
        "hcid": [],
    }

    variable_values_gr = {
        "legacyId": 61771675
    }

    variable_values_gr_search = {
      "query": "dungeon crawler carl"
    }

    result_hc = hardcover.search(variable_values_hc)
    result_gr = goodreads.legacy_id(variable_values_gr)
    # result_search = goodreads.search(variable_values_gr_search)
    print(result_hc)
    print(result_gr)

if __name__ == "__main__":
    main()