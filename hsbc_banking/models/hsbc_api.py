# -*- utf-8 -*-

import requests
from pgpy import PGPKey, PGPMessage, PGPSignature
import json
import base64
import xml.etree.ElementTree as ET
from datetime import datetime
import os
import inspect

def get_full_path(file_path):
    directory_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    full_path = os.path.join(directory_path, file_path)
    return full_path

def bulk_payments_api(debtor, creditors, api_params, data_params):
    url = api_params.get('url')
    headers = {
        'Content-Type': 'application/json',
        'x-hsbc-client-id': api_params.get('client_id'),
        'x-hsbc-client-secret': api_params.get('client_secret'),
        'x-hsbc-profile-id': api_params.get('profile_id'),
        'x-payload-type': api_params.get('payload_type'),
    }

    with open(get_full_path('./../static/src/bulk_xml_format.xml'), 'r') as f:
        data_xml = f.read()

    no_trs = len(creditors)
    # Prepare XML for multiple CreditorTransaction
    cdtr_end = data_xml.find('</CdtTrfTxInf>') + 15
    cdtr_str = data_xml[data_xml.find('<CdtTrfTxInf>'):cdtr_end]
    cdtrs_str = cdtr_str * (no_trs - 1) #length of creditors - 1
    data_xml = data_xml[:cdtr_end] + cdtrs_str + data_xml[cdtr_end:]


    ET.register_namespace('', 'urn:iso:std:iso:20022:tech:xsd:pain.001.001.03')
    root = ET.fromstring(data_xml)
    now_time = datetime.now()
    msg_id = f"biw{now_time.timestamp()}HSBC"
    root[0][0][0].text = msg_id  #<MsgId>  #done
    now_str = str(now_time)
    now_str = now_str[:now_str.find('.')].replace(' ', 'T')
    root[0][0][1].text = now_str  #<CreDtTm> #done
    root[0][0][2][0].text = 'FDET'  # <Authstn><Cd>Store as parameter somewhere #done
    root[0][0][3].text = str(no_trs)  # <NbOfTxs> #done
    root[0][0][4].text = debtor['amount']  # <CtrlSum> #done
    root[0][0][5][0][0][0][0].text = api_params.get('profile_id')  # <InitgPty><Id><OrgId><Id> #done
    batch_ref = f"Batch {now_str}"
    root[0][1][0].text = batch_ref  # <PmtInfId>  #done
    root[0][1][1].text = 'TRF'  # <PmtMtd>Store as parameter somewhere #done
    root[0][1][2][0][0].text = 'URNS'  # <PmtTpInf><SvcLvl><Cd>Store as parameter somewhere #done
    root[0][1][3].text = str(datetime.today().date())  # <ReqdExctnDt> #done
    root[0][1][4][0].text = debtor['name'] # <Dbtr><Nm> #done
    root[0][1][4][1][0].text = debtor['addr1']   # <StrtNm> #done
    root[0][1][4][1][1].text = debtor['addr2']  # <BldgNb> #done
    root[0][1][4][1][2].text = debtor['zip']  # <PstCd> #done
    root[0][1][4][1][3].text = debtor['city']  # <TwnNm> #done
    root[0][1][4][1][4].text = debtor['country_code']  # <Ctry> #done
    root[0][1][5][0][0][0].text = debtor['acc_no']  # <DbtrAcct><Id><Othr><Id> #done
    root[0][1][6][0][0].text = debtor['ifsc']  # <DbtrAgt><FinInstnId><BIC> #done
    root[0][1][6][0][1].text = debtor['bank_name']  # <Nm> #done
    root[0][1][6][0][2][0].text = 'IN'  # <PstlAdr><Ctry>Store as static parameter somewhere #done
    root[0][1][7].text = 'DEBT' #done

    for i in range(no_trs):
        root[0][1][8+i][0][0].text = data_params['transaction_refs'][i]  # <InstrId> #done
        root[0][1][8+i][0][1].text = data_params['transaction_refs'][i]  # <EndToEndId> #done
        root[0][1][8+i][1][0].text = creditors[i]['amount']  # <InstdAmt Ccy="INR">Make currency dynamic? #done
        root[0][1][8+i][2][0][0][0].text = creditors[i]['ifsc']  # <CdtrAgt><FinInstnId><ClrSysMmbId><MmbId> #done
        root[0][1][8+i][2][0][1].text = creditors[i]['bank_name'] #done
        root[0][1][8+i][2][0][2][0].text = 'IN'  # Customer's Bank Country Code #done
        # <Cdtr> <PstlAdr>
        root[0][1][8+i][3][0].text = creditors[i]['name']  # Customer Name Get from contact master #done
        root[0][1][8+i][3][1][0].text = creditors[i]['addr1']  # Customer Address Get from contact master #done
        root[0][1][8+i][3][1][1].text = creditors[i]['addr2']  # Customer Address Get from contact master #done
        root[0][1][8+i][3][1][2].text = creditors[i]['zip']  # Customer Address Get from contact master #done
        root[0][1][8+i][3][1][3].text = creditors[i]['city']  # Customer Address Get from contact master #done
        root[0][1][8+i][3][1][4].text = creditors[i]['state']  # Customer Address Get from contact master #done
        root[0][1][8+i][3][1][5].text = 'IN'  # Customer Address Get from contact master #done
        root[0][1][8+i][4][0][0][0].text = creditors[i]['acc_no']  # <CdtrAcct><Id><Othr><Id>Customer Bank Acc Number #done
        

    res_xml = ET.tostring(root)
    data_xml = res_xml.decode()
    pgp_data_xml = PGPMessage.new(data_xml)
    pgp_data_signed = pgp_data_xml

    skey, _ = PGPKey.from_file(get_full_path('./../static/src/keys/'+api_params.get('private_key')))
    passphrase = api_params.get('pass')
    with skey.unlock(passphrase) as uskey:
        pgp_data_signed |= uskey.sign(data_xml)

    print("after skey")

    pkey, _ = PGPKey.from_file(get_full_path('./../static/src/keys/'+api_params.get('public_key')))
    encrypted_message = pkey.encrypt(pgp_data_signed)
    payment_data = base64.b64encode(str(encrypted_message).encode()).decode()

    print("after pkey")

    data = {"paymentBase64": payment_data}

    response = requests.post(url=url, headers=headers, json=data)

    response_json = json.loads(response.content.decode())

    reference_id = response_json.get('referenceId')
    response_base64 = response_json.get('responseBase64')

    decrypted_response = ''
    verified = False
    if response_base64:
        response_decoded = base64.b64decode(response_base64.encode()).decode()
        response_message = PGPMessage.from_blob(response_decoded)
        dkey, _ = PGPKey.from_file(get_full_path('./../static/src/keys/'+api_params.get('private_key')))
        with dkey.unlock(passphrase) as udkey:
            response_decrypt = udkey.decrypt(response_message)
        signature = pkey.verify(response_decrypt)
        decrypted_response = response_decrypt.message.decode()
        verified = True

        print("It's just before the end")

    return msg_id, batch_ref, data_xml, response, reference_id, decrypted_response, verified


def payments_status_enquiry_api(api_params, transaction_ref, batch_ref, response_ref):
    url = api_params.get('url')
    headers = {
        'Content-Type': 'application/json',
        'x-hsbc-client-id': api_params.get('client_id'),
        'x-hsbc-client-secret': api_params.get('client_secret'),
        'x-hsbc-profile-id': api_params.get('profile_id'),
        'x-payload-type': api_params.get('payload_type'),
    }
    msg_id = f"biw{datetime.now().timestamp()}HSBC"

    with open(get_full_path('./../static/src/payment_status_enquiry_xml_format.xml'), 'r') as f:
        data_xml = f.read()

    ET.register_namespace('', 'urn:iso:std:iso:20022:tech:xsd:pain.001.001.03')
    root = ET.fromstring(data_xml)
    root[0].text = api_params.get('profile_id')
    root[1][0].text = response_ref
    # root[1][1].text = msg_id
    # root[1][2].text = batch_ref
    root[1][3].text = transaction_ref
    res_xml = ET.tostring(root)

    data_xml = res_xml.decode()
    pgp_data_xml = PGPMessage.new(data_xml)
    pgp_data_signed = pgp_data_xml
    skey, _ = PGPKey.from_file(get_full_path('./../static/src/keys/'+api_params.get('private_key')))
    passphrase = api_params.get('pass')
    with skey.unlock(passphrase) as uskey:
        pgp_data_signed |= uskey.sign(data_xml)

    pkey, _ = PGPKey.from_file(get_full_path('./../static/src/keys/'+api_params.get('public_key')))
    encrypted_message = pkey.encrypt(pgp_data_signed)
    payment_data = base64.b64encode(str(encrypted_message).encode()).decode()

    data = {"paymentEnquiryBase64": payment_data}
    response = requests.post(url=url, headers=headers, json=data)
    response_json = json.loads(response.content.decode())
    reference_id = response_json.get('referenceId')
    response_base64 = response_json.get('responseBase64')

    decrypted_response = ''
    verified = False
    if response_base64:
        response_decoded = base64.b64decode(response_base64.encode()).decode()
        response_message = PGPMessage.from_blob(response_decoded)
        dkey, _ = PGPKey.from_file(get_full_path('./../static/src/keys/'+api_params.get('private_key')))
        with dkey.unlock(passphrase) as udkey:
            response_decrypt = udkey.decrypt(response_message)
        signature = pkey.verify(response_decrypt)
        decrypted_response = response_decrypt.message.decode()
        verified = signature._subjects[0].verified



    return msg_id, batch_ref, data_xml, response, reference_id, decrypted_response, verified

