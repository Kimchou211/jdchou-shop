from flask import Flask, render_template, jsonify, request
from bakong_khqr import KHQR
import time
import os

app = Flask(__name__)

# Token របស់អ្នក - ប្រសិនបើនៅតែបង្កើតមិនចេញ អ្នកប្រហែលជាត្រូវប្តូរ Token ថ្មី
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
        # ប្រសិនបើ Frontend មិនបានផ្ញើ amount មក វានឹងប្រើតម្លៃ ១០០០ រៀលជាគោល
        total_amount = float(data.get('amount', 1000))
        
        bill_number = f"INV{int(time.time())}"
        
        # បង្កើត QR
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

        # ឆែកមើលថា តើ qr_string បង្កើតបានជោគជ័យឬទេ
        if not qr_string:
            print("❌ Error: QR String is empty. Token might be expired.")
            return jsonify({"status": "error", "message": "មិនអាចបង្កើត QR បានទេ (Token Error)"}), 500

        md5 = khqr.generate_md5(qr=qr_string)
        
        payment_db[bill_number] = {
            "md5": md5,
            "status": "pending",
            "amount": total_amount
        }

        # ទាញយក Domain របស់ Render ដោយស្វ័យប្រវត្តិ
        base_url = request.host_url.rstrip('/')
        
        deeplink_url = khqr.generate_deeplink(
            qr=qr_string,
            callback=f"{base_url}/",
            appIconUrl="https://dummyimage.com/200x200/E02B20/fff&text=Jdchou",
            appName="Jdchou Shop"
        )

        return jsonify({
            "status": "success",
            "qr_string": qr_string,
            "bill_number": bill_number,
            "amount": total_amount,
            "deeplink": deeplink_url
        })
    except Exception as e:
        print(f"❌ Critical Error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/status/<bill_number>', methods=['GET'])
def check_status(bill_number):
    if bill_number not in payment_db:
        return jsonify({"status": "not_found"})
    
    record = payment_db[bill_number]
    if record["status"] == "success":
        return jsonify({"status": "success"})

    try:
        response = khqr.check_payment(record["md5"])
        if str(response).strip().upper() == "PAID":
            record["status"] = "success"
            return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error checking status: {e}")

    return jsonify({"status": "pending"})

if __name__ == '__main__':
    # សម្រាប់ការដាក់លើ Render ត្រូវប្រើ Host 0.0.0.0 និង Port ពី Environment
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
