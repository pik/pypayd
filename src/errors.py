class PyPayError(Exception):
    pass

class PriceInfoError(PyPayError):
    pass

class PaymentProcessingError(PyPayError):
    pass

class PollingError(PyPayError):
    pass
