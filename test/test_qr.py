import unittest
import subprocess
from base64 import b64decode
from pypayd import qr

#There appears to be only one up-to-date python library for decoding QRCodes
#It does not have an automated install, it is python2 only and it depends on Zbars
#So just test using checkout_put w/ Zbars or skip test if Zbars does not exist.

class QRCode(unittest.TestCase):

    def test_gen_qr(self):
        payload_in = "1HB5XMLmzFVj8ALj6mfBsbifRoD4miY36v"
        qr_image = qr.bitcoinqr(payload_in)
        #convert from web to img form
        qr_image = qr_image.replace("data:image/png;base64,", '', 1)
        qr_image = b64decode(qr_image.encode('utf-8'))
        with open("test/qr_test.png", "wb") as wfile:
            wfile.write(qr_image)
        try:
            payload_out = subprocess.check_output(['zbarimg', '-q', 'test/qr_test.png'])
            self.assertEqual(payload_out.decode('utf-8').rstrip('\n'), "QR-Code:bitcoin:" + payload_in)
        except FileNotFoundError:
            print("zbarimg not found skipping qr test")

    def setUpClass():
        try:
            subprocess.check_output(['zbarimg', '-h'])
        except FileNotFoundError:
            unittest.skip(QRCode.test_gen_qr)

if __name__ == '__main__':
    unittest.main()
