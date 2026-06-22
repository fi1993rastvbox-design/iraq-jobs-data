import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging
from firebase_admin import firestore

# تهيئة فايربيس باستخدام ملف مفتاح الخدمة
# تأكد من وضع مسار الملف الصحيح إذا قمت بنقله
cred = credentials.Certificate('../assets/service-account.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

def send_notification_to_all_users(title, body, data=None):
    """
    ترسل هذه الدالة إشعاراً لجميع المستخدمين الذين لديهم FCM Token
    """
    print(f"جاري البحث عن المستخدمين لإرسال إشعار: {title}")
    users_ref = db.collection('users')
    docs = users_ref.stream()

    tokens = []
    for doc in docs:
        user_data = doc.to_dict()
        token = user_data.get('fcmToken')
        if token:
            tokens.append(token)

    if not tokens:
        print("لم يتم العثور على أي أجهزة مسجلة لتلقي الإشعارات.")
        return

    print(f"تم العثور على {len(tokens)} جهاز. جاري الإرسال...")

    # إرسال الإشعار باستخدام Multicast (إرسال دفعة واحدة لعدة أجهزة)
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        data=data or {},
        tokens=tokens,
    )

    response = messaging.send_multicast(message)
    print(f"تم إرسال {response.success_count} بنجاح، وفشل {response.failure_count}.")

def send_notification_to_category(category, title, body, data=None):
    """
    ترسل إشعاراً فقط للمستخدمين المهتمين بتخصص معين
    يفترض أنك تحفظ اهتمامات المستخدمين في حقل "interests" أو "category"
    """
    print(f"جاري إرسال إشعار للمهتمين بتخصص: {category}")
    users_ref = db.collection('users').where('category', '==', category)
    docs = users_ref.stream()
    
    tokens = []
    for doc in docs:
        token = doc.to_dict().get('fcmToken')
        if token:
            tokens.append(token)
            
    if tokens:
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            tokens=tokens,
        )
        messaging.send_multicast(message)
        print(f"تم الإرسال لـ {len(tokens)} مستخدمين مهتمين بـ {category}.")

if __name__ == '__main__':
    # مثال على الاستخدام التجريبي:
    print("نظام إشعارات الوظائف - يعمل بالخلفية")
    # send_notification_to_all_users(
    #     title="وظيفة جديدة متاحة!",
    #     body="تم نشر وظيفة جديدة في تخصص الهندسة المدنية، قدم الآن.",
    #     data={"job_id": "12345"}
    # )
