from flask import Flask, render_template, jsonify, request
from bakong_khqr import KHQR
import time
import os

app = Flask(__name__)

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiOGEwZDkzMTc2ZTA2NDNhYiJ9LCJpYXQiOjE3NzE5NTAxMDksImV4cCI6MTc3OTcyNjEwOX0.4tSwUE2vC-8ZfHFOxrG2z9wuL8DcC_Y5GP2V-Yoxg8o"
khqr = KHQR(TOKEN)

payment_db = {}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/checkout', methods=['POST'])
def checkout():
    try:
        data = request.json
        total_amount = float(data.get('amount', 0))
        
        if total_amount <= 0:
            return jsonify({"status": "error", "message": "មិនមានទំនិញក្នុងកន្ត្រកទេ"})

        bill_number = f"INV{int(time.time())}"
        
        # បង្កើតតែ QR String មិនបាច់ហៅ API ទៅ Bakong ទេ
        qr_string = khqr.create_qr(
            bank_account="kimchou_kren@bkrt",
            merchant_name="Jdchou",
            merchant_city="phnom penh",
            amount=total_amount,
            currency="KHR",
            store_label="jdchoushop",
            phone_number="085890059",
            bill_number=bill_number,
            terminal_label="webQR",
            static=False,
        )

        md5 = khqr.generate_md5(qr=qr_string)
        
        payment_db[bill_number] = {
            "md5": md5,
            "status": "pending",
            "amount": total_amount
        }

        # លែងមានកូដ generate_deeplink ទៀតហើយ ដើម្បីកុំឲ្យ Render គាំង
        return jsonify({
            "status": "success",
            "qr_string": qr_string,
            "bill_number": bill_number,
            "amount": total_amount
        })
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({"status": "error", "message": "មានបញ្ហាក្នុងការបង្កើត QR"}), 500

@app.route('/api/status/<bill_number>', methods=['GET'])
def check_status(bill_number):
    if bill_number not in payment_db:
        return jsonify({"status": "not_found"})
    
    record = payment_db[bill_number]
    if record["status"] == "success":
        return jsonify({"status": "success"})

    try:
        # មុខងារឆែក Status នេះទោះជា Render ក៏វាមិនសូវ Block ដែរ
        response = khqr.check_payment(record["md5"])
        if str(response).strip().upper() == "PAID":
            record["status"] = "success"
            return jsonify({"status": "success"})
    except Exception as e:
        pass 

    return jsonify({"status": "pending"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
