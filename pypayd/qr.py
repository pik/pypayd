import qrcode
import io
from base64 import b64encode
import logging
#I can decode the addresses produced correctly but the data load does not appear to be identical to blockchain.info QR, not sure what's wrong

def bitcoinqr(address, pixel_size=4, border_pixsels=0):
    return qrcode_datauri('bitcoin:%s' %(address), pixel_size)

def qrcode_datauri(data, pixel_size=6, border_pixels=1, error_correction="H"):
    logging.debug(data)
    qrcode_object = qrcode.QRCode(
        error_correction=getattr(
            qrcode.constants,
            "ERROR_CORRECT_%s" % error_correction,
            "H"
        ),
        box_size=max(1, min(100, pixel_size)),
        border=max(1, min(100, border_pixels)),
    )
    qrcode_object.add_data(data)
    qrcode_object.make(fit=True)
    qrcode_image = qrcode_object.make_image()
    byte_stream = io.BytesIO()
    qrcode_image.save(byte_stream)
    datauri = "data:image/png;base64,%s" % (b64encode(byte_stream.getvalue()).decode('utf-8'))
    byte_stream.close()
    return datauri
