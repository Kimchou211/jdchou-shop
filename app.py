from flask import Flask, render_template, jsonify, request
from bakong_khqr import KHQR
import time
import os

app = Flask(__name__)

# ១. រៀបចំ Token និង KHQR (គួរដាក់ក្នុង Environment Variables ពេលដាក់លើ Render ដើម្បីសុវត្ថិភាព)
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXRhIjp7ImlkIjoiOGEwZDkzMTc2ZTA2NDNhYiJ9LCJpYXQiOjE3NzE5NTAxMDksImV4cCI6MTc3OTcyNjEwOX0.4tSwUE2vC-8ZfHFOxrG2z9wuL8DcC_Y5GP2V-Yoxg8o"
khqr = KHQR(TOKEN)

# Database បណ្តោះអាសន្នសម្រាប់ផ្ទុកទិន្នន័យការបង់ប្រាក់
payment_db = {}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/checkout', methods=['POST'])
def checkout():
    # ទទួលទិន្នន័យតម្លៃសរុបពីកន្ត្រកទំនិញ (Frontend)
    data = request.json
    total_amount = float(data.get('amount', 0))
    
    if total_amount <= 0:
        return jsonify({"status": "error", "message": "មិនមានទំនិញក្នុងកន្ត្រកទេ"})

    bill_number = f"INV{int(time.time())}"
    
    # បង្កើត QR String តាមតម្លៃជាក់ស្តែងដែលអតិថិជនបានទិញ
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

    # បង្កើត MD5 សម្រាប់ឆែក Status ជាមួយ Bakong
    md5 = khqr.generate_md5(qr=qr_string)
    
    # រក្សាទុកក្នុង Database
    payment_db[bill_number] = {
        "md5": md5,
        "status": "pending",
        "amount": total_amount
    }

    # ==========================================
    # ចំណុចសំខាន់សម្រាប់ Render & Mobile Deeplink
    # ==========================================
    # ទាញយក URL ពិតប្រាកដរបស់ Website ពេលកំពុង Run (ឧ. https://jdchou.onrender.com)
    base_url = request.host_url.rstrip('/')
    
    # បង្កើត Deeplink ដោយប្រើ URL នោះ
    deeplink_url = khqr.generate_deeplink(
        qr=qr_string,
        callback=f"{base_url}/", # ឲ្យ App ធនាគារលោតមក Website វិញពេលបង់រួច
        appIconUrl="https://dummyimage.com/200x200/E02B20/fff&text=Jdchou", # Logo ហាងរបស់អ្នកពេលលោតចូល App ធនាគារ
        appName="Jdchou Shop"
    )

    return jsonify({
        "status": "success",
        "qr_string": qr_string,
        "bill_number": bill_number,
        "amount": total_amount,
        "deeplink": deeplink_url
    })

@app.route('/api/status/<bill_number>', methods=['GET'])
def check_status(bill_number):
    if bill_number not in payment_db:
        return jsonify({"status": "not_found"})
    
    record = payment_db[bill_number]
    
    # បើធ្លាប់ឆែកឃើញថាជោគជ័យហើយ មិនបាច់សួរទៅ Bakong ទៀតទេ
    if record["status"] == "success":
        return jsonify({"status": "success"})

    try:
        # ហៅទៅ Bakong API ដើម្បីផ្ទៀងផ្ទាត់
        response = khqr.check_payment(record["md5"])
        print(f"Bakong Response for {bill_number}: {response}")

        # ឆែកមើលថាតើលទ្ធផលមានពាក្យ "PAID" ដែរឬទេ
        if str(response).strip().upper() == "PAID":
            record["status"] = "success"
            return jsonify({"status": "success"})

    except Exception as e:
        print(f"Error checking Bakong: {e}")

    return jsonify({"status": "pending"})

if __name__ == '__main__':
    # កំណត់ Port ស្វ័យប្រវត្តិសម្រាប់ Render បើមិនមានទេ ប្រើ 5000 សម្រាប់ Local កុំព្យូទ័រ
    port = int(os.environ.get("PORT", 5000))
    # host='0.0.0.0' អនុញ្ញាតឲ្យ Server ខាងក្រៅ (ដូចជា Render) អាចភ្ជាប់ចូលបាន
    app.run(host='0.0.0.0', port=port, debug=True)
