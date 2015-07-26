#!/usr/bin/env python3
import argparse
import appdirs
import logging
import logging.handlers
import os
import sys
import time
from configobj import ConfigObj
from src import wallet, db, payments, api, config
from ast import literal_eval

def try_type_eval(val):
    try:
        return literal_eval(val)
    except:
        return val

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='pypayd', description='A small daemon for processing bitcoin payments')
    subparsers = parser.add_subparsers(dest='action', help='available actions')


    parser.add_argument("-S","--server", help="run pypayd", action='store_true')
    parser.add_argument('-V', '--version', action='version', version="pypayd v%s" % config.VERSION)
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', default=False, help='sets log level to DEBUG instead of WARNING')
    parser.add_argument('--testnet', action='store_true',default=False, help='run on Bitcoin testnet')
    parser.add_argument('--data-dir', help='override default directory for config and db files')
    parser.add_argument('--config-file', help='the location of the configuration file')
    parser.add_argument('--log-file', help='the location of the log file')
    parser.add_argument('--pid-file', help='the location of the pid file')

    parser.add_argument('--rpc-host', help='the IP of the interface to bind to for providing API access (0.0.0.0 for all interfaces)')
    parser.add_argument('--rpc-port', type=int, help='port on which to provide API access')
    parser_wallet = subparsers.add_parser('wallet', help='access pypayd wallet from command-line')
    parser_wallet.add_argument("--from-mnemonic", help="load wallet info from mnemonic passphrase")
    parser_wallet.add_argument("--mnemonic-type", help="specify the mnemonic interface to load")
    parser_wallet.add_argument("--from-file", help="load wallet info from specified file", nargs= '?', const=config.DEFAULT_WALLET_FILE)
    parser_wallet.add_argument("--decrypt-pw", help="password to decrypt wallet file")
    parser_wallet.add_argument("--from-entropy", help="load wallet from entropy")
    parser_wallet.add_argument("--to-file", help="save wallet in specified file", nargs= '?', const=config.DEFAULT_WALLET_FILE)
    parser_wallet.add_argument("--encrypt-pw", help="password to encrypt wallet file")
    parser_wallet.add_argument("--to-console", help="togle to output wallet hwif to console", nargs='?', const=True)
    parser_wallet.add_argument("--output-private", help="toggle to output the private key", nargs='?', const=True)
    parser_wallet.add_argument("--overwrite", help="toggle to overwrite existing wallet file")

    args= parser.parse_args()

    def exitPyPay(message, exit_status = 0):
        logging.info(message)
        sys.exit(exit_status)

    if len(sys.argv) < 2:
        exitPyPay("No arguments received, exiting...")

    if not config.__dict__.get('DATA_DIR'):
        config.DATA_DIR = args.data_dir or appdirs.user_data_dir(appauthor='pik', appname='pypayd', roaming=True)
    if not os.path.exists(config.DATA_DIR):
        os.makedirs(config.DATA_DIR)
    #read the .conf file and stuff it into config.py
    print("Loading config settings...")
    conf_file = os.path.join((args.config_file or config.DATA_DIR), "pypayd.conf")
    if not os.path.exists(conf_file):
        with open(conf_file, 'w') as wfile:
            wfile.write("[Default]")
    conf = ConfigObj(conf_file)
    #This will raise on a conf file without a [Default] field and will not set values that are not in config.py
    #Might change this behaviour later
    for field, value in conf['Default'].items():
        try:
            if field.upper() in config.__dict__.keys():
                config.__dict__[field.upper()] = (try_type_eval(value))
        except:
            print("Error handling config file field %s, %s" %(field, value))

    #set standard values to default or args values if they have not been set
    if not config.__dict__.get('PID'):
        config.PID = (args.pid_file or os.path.join(config.DATA_DIR, "pypayd.pid"))
    if not config.__dict__.get("LOG"):
        config.LOG = (args.log_file or os.path.join(config.DATA_DIR, "pypayd.log"))
    config.RPC_PORT = (args.rpc_port or config.RPC_PORT)
    config.RPC_HOST = (args.rpc_host or config.RPC_HOST)
    config.TESTNET = (True if args.testnet else config.TESTNET)
    if not config.__dict__.get('DB'):
        config.DB = config.DEFAULT_TESTNET_DB if config.TESTNET else config.DEFAULT_DB
    if not config.__dict__.get('KEYPATH'):
        config.KEYPATH = config.DEFAULT_KEYPATH

    #write pid to file
    pid = str(os.getpid())
    pid_file = open(config.PID, 'w')
    pid_file.write(pid)
    pid_file.close()

    #logging
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)
    fileh = logging.handlers.RotatingFileHandler(config.LOG, maxBytes=config.MAX_LOG_SIZE, backupCount=5)
    fileh.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(message)s', '%Y-%m-%d-T%H:%M:%S%z')
    fileh.setFormatter(formatter)
    logger.addHandler(fileh)
    #So we aren't spammed with requests creating new connections every poll
    logging.getLogger("requests").setLevel(logging.WARN)

    #print(args, "\n")
    if args.action == 'wallet':
        if not (args.from_mnemonic or args.from_file):
            exitPyPay("No arguments provided for wallet, Exiting...")
        if args.from_mnemonic:
            pypay_wallet = wallet.PyPayWallet.fromMnemonic(args.from_mnemonic)
        elif args.from_file:
            pypay_wallet = wallet.PyPayWallet.fromEncryptedFile(password= (args.decrypt_pw or config.DEFAULT_WALLET_PASSWORD), file_name=os.path.join(config.DATA_DIR, args.from_file))
        if not pypay_wallet: exitPyPay("Unable to load wallet, Exiting...")
        logging.info("Wallet loaded: %s\nKeypath: %s" %(pypay_wallet.hwif(), str(pypay_wallet.keypath)))

    if args.server:
        try:
            assert(pypay_wallet)
        except NameError:
             exitPyPay("A wallet is required for running the server, Exiting...")
        print(config.DATA_DIR, config.DB, "\n")
        database = db.PyPayDB(os.path.join(config.DATA_DIR, config.DB))
        logging.info("DB loaded: %s" %config.DB)
        if not database:
            exitPyPay("Unable to load SQL database, Exiting...")
        payment_handler = payments.PaymentHandler(database=database, wallet=pypay_wallet, bitcoin_interface_name = config.BLOCKCHAIN_SERVICE)
        if not payment_handler:
             exitPyPay("Unable to start Payment Handler, Exiting...")
        #logging.info("Testing priceinfo ticker: %s BTC/USD" %(payment_handler.checkPriceInfo()))
        logging.info("Testing Blockchain connection %s" %str(payment_handler.checkBlockchainService()))
        api_serv = api.API()
        try:
            logging.info("Payment Handler loaded, starting auto-poller..")
            payment_handler.run()
            api_serv.serve_forever(payment_handler, threaded=False)
        except KeyboardInterrupt:
            api_serv.server.stop()
        #If wallet output was requested don't quit just yet
        if args.action == 'wallet' and (args.to_console or args.to_file): pass
        else:
            exitPyPay("Interrupted, Exiting...")

    if args.action == 'wallet' and pypay_wallet:
        if args.to_console:
            logging.info("Dumping wallet info to console")
            print("Current keypath: ", str(pypay_wallet.keypath))
            print("Public hwif: ", pypay_wallet.hwif())
            if args.output_private:
                try:
                    print("Private hwif: ", pypay_wallet.hwif(True))
                except NameError:
                    print("No Private part for key")
        if args.to_file:
            if not args.encrypt_pw:
                logging.info("No encryption password provided for wallet, skipping")
                pass
            else:
                pypay_wallet.toEncryptedFile(password = args.encrypt_pw, file_name = (args.to_file or config.DEFAULT_WALLET_FILE), store_private = args.output_private, force=args.overwrite)



