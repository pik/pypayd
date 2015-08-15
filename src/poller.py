class PyPayPoller(object):

    def __init__(self, payment_handlers = []):
        '''init a PyPayPoller - a payment_handler correponds to a single master-public key'''
        self.payment_handlers = []

    def add_payment_handler(self, payment_handler):
        self.payment_handlers.append(payment_handler)

    #Runs address polling for new payments
    def run(self):
        self.poller_thread = threading.Thread(target=self._run, daemon=True)
        self.poller_thread.start()
        return self.poller_thread.is_alive(), self.poller_thread.ident

    def _run(self, polling_delay=config.POLLING_DELAY):
        while True:
            t = time.time()
            #Fetch active address async, set last polled time
            self.pollActiveAddresses()
            time.sleep((config.POLLING_DELAY - (time.time() - t)))
