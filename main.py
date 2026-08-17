import os, sqlite3, threading, time, urllib.parse, webbrowser, shutil, re
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from flask import Flask, request, redirect, url_for, render_template_string, flash, send_file

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.environ.get('LOCALAPPDATA', APP_DIR), 'Trend Center Jordan')
DB_PATH = os.path.join(DATA_DIR, 'trend_center.db')
DOCUMENTS_DIR = os.path.join(DATA_DIR, 'documents')
DESKTOP_DIR = os.path.join(os.path.expanduser('~'), 'Desktop')
CONTRACTS_DIR = os.path.join(DESKTOP_DIR, 'عقود الصيانة')
WHATSAPP_DIR = os.path.join(DATA_DIR, 'whatsapp_session')
CATALOG_DIR = os.path.join(DATA_DIR, 'catalog_images')
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(CONTRACTS_DIR, exist_ok=True)
os.makedirs(WHATSAPP_DIR, exist_ok=True)
os.makedirs(CATALOG_DIR, exist_ok=True)
app = Flask(__name__)
app.secret_key = 'trend-center-jordan-local'

CHECKS = ['الشاشة', 'اللمس', 'الكاميرات', 'السماعة', 'المايكروفون', 'الشحن', 'الشبكة والاتصال', 'البصمة أو Face ID', 'الأزرار', 'الهيكل الخارجي', 'الماء أو الرطوبة', 'الملحقات']

BASE = '''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{ title }} | ترند سنتر الأردن</title><style>
@font-face{font-family:TahomaLocal;src:local("Arial")}*{box-sizing:border-box}body{margin:0;background:#f4f7fa;color:#1f2933;font-family:TahomaLocal,Tahoma,Arial,sans-serif;font-weight:700}header{background:linear-gradient(135deg,#102a43,#0b7285);color:#fff;padding:22px 5%;display:flex;justify-content:space-between;align-items:center;gap:20px}header h1{margin:0;font-size:25px}.tcj-logo{display:inline-flex;align-items:center;justify-content:center;width:48px;height:48px;margin-left:12px;border:2px solid #d4a72c;border-radius:12px;color:#d4a72c;font-size:18px;letter-spacing:1px;vertical-align:middle}header small{display:block;opacity:.8;margin-top:6px}.brand-en{direction:ltr;font-size:12px;letter-spacing:1px}.wrap{max-width:1250px;margin:25px auto;padding:0 18px}.nav{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px}.btn,a.btn{border:0;border-radius:9px;padding:11px 17px;background:#0b7285;color:#fff;text-decoration:none;cursor:pointer;font-weight:700}.btn.secondary{background:#e8eef3;color:#1f3a4d}.btn.green{background:#167d8d}.btn.orange{background:#d4a72c}.btn.red{background:#bd4051}.card{background:#fff;border-radius:15px;padding:22px;margin-bottom:18px;box-shadow:0 7px 22px #17324d12}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.wide{grid-column:span 2}.full{grid-column:1/-1}label{display:block;margin-bottom:6px;color:#33445a}input,select,textarea{width:100%;padding:12px;border:1px solid #cfdae6;border-radius:8px;font:inherit;background:#fbfdff}textarea{min-height:80px}.checks{display:grid;grid-template-columns:repeat(4,1fr);gap:9px}.check{background:#eef5f7;padding:10px;border-radius:8px;font-size:13px}.check input{width:auto;margin-left:7px}table{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden}th,td{padding:12px 9px;border-bottom:1px solid #e7edf3;text-align:right;font-size:13px}th{background:#e6f1f4;color:#0b5968}.badge{padding:6px 10px;border-radius:20px;background:#e7eef5;font-size:12px}.badge.received{background:#fff3cd;color:#856404}.badge.ready{background:#d9f0f3;color:#0b5968}.badge.delivered{background:#e2e8f0;color:#334e68}.actions{display:flex;gap:6px;flex-wrap:wrap}.notice{padding:12px;border-radius:9px;background:#e6f1f4;color:#0b5968;margin-bottom:15px}.muted{color:#6b7a8d;font-size:13px}@media(max-width:850px){.grid{grid-template-columns:repeat(2,1fr)}.wide{grid-column:span 2}.checks{grid-template-columns:repeat(2,1fr)}}
</style></head><body><header><div><h1><span class="tcj-logo">TCJ</span>ترند سنتر الأردن</h1><small>مركز صيانة الأجهزة الخلوية</small></div><div class="brand-en">TREND CENTER JORDAN</div></header><main class="wrap"><div class="nav"><a class="btn" href="{{ url_for('home') }}">لوحة الأجهزة</a><a class="btn green" href="{{ url_for('new_device') }}">+ استلام جهاز جديد</a><a class="btn secondary" href="{{ url_for('settings') }}">إعدادات المحل</a><a class="btn secondary" href="{{ url_for('catalog') }}">كتالوج الأجهزة</a><a class="btn secondary" href="{{ url_for('customers') }}">العملاء</a><a class="btn secondary" href="{{ url_for('reports') }}">التقارير</a></div>{% with messages=get_flashed_messages() %}{% if messages %}<div class="notice">{{ messages[0] }}</div>{% endif %}{% endwith %}{{ body|safe }}</main></body></html>'''

def db():
    con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row; return con

def init_db():
    con=db()
    con.execute('''CREATE TABLE IF NOT EXISTS devices(id INTEGER PRIMARY KEY AUTOINCREMENT, receipt_no TEXT, created_at TEXT, owner TEXT, phone TEXT, brand TEXT, model TEXT, imei TEXT, repair TEXT, checks TEXT, notes TEXT, status TEXT DEFAULT 'مستلم', received_at TEXT, ready_at TEXT, delivered_at TEXT)''')
    con.execute('''CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY,v TEXT)''')
    con.execute('''CREATE TABLE IF NOT EXISTS device_catalog(id INTEGER PRIMARY KEY AUTOINCREMENT, brand TEXT NOT NULL, model TEXT NOT NULL, image_filename TEXT, created_at TEXT)''')
    if con.execute('SELECT COUNT(*) FROM device_catalog').fetchone()[0] == 0:
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        starter = [('Apple','iPhone 11'),('Apple','iPhone 13'),('Apple','iPhone 14 Pro Max'),('Samsung','Galaxy A56'),('Samsung','Galaxy S23 Ultra'),('Huawei','P40 Pro'),('Xiaomi','Redmi Note 13')]
        con.executemany('INSERT INTO device_catalog(brand,model,image_filename,created_at) VALUES(?,?,?,?)', [(b,m,'',now) for b,m in starter])
    con.commit(); con.close()

def setting(k, default=''):
    con=db(); r=con.execute('SELECT v FROM settings WHERE k=?',(k,)).fetchone(); con.close(); return r['v'] if r else default

def rtl(value):
    value = '' if value is None else str(value)
    return get_display(reshape(value))


def safe_filename(value):
    value = (value or 'عميل').strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', value)
    return value[:80] or 'عميل'


def save_document_to_desktop(device, kind, source_path):
    labels = {'received': 'عقد استلام', 'ready': 'إشعار جاهزية', 'delivered': 'عقد تسليم'}
    customer = safe_filename(device['owner'])
    receipt = safe_filename(device['receipt_no'])
    filename = f"{labels.get(kind, 'عقد صيانة')} - {customer} - {receipt}.png"
    target = os.path.join(CONTRACTS_DIR, filename)
    shutil.copy2(source_path, target)
    return target


def _font(size, bold=True):
    candidates = []
    if os.name == 'nt':
        candidates += [r'C:\\Windows\\Fonts\\arialbd.ttf', r'C:\\Windows\\Fonts\\tahomabd.ttf'] if bold else [r'C:\\Windows\\Fonts\\arial.ttf', r'C:\\Windows\\Fonts\\tahoma.ttf']
    candidates += ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_document_image(device, kind):
    shop = setting('shop_name', 'ترند سنتر الأردن')
    en = setting('shop_en', 'TREND CENTER JORDAN')
    titles = {'received': 'وثيقة استلام جهاز', 'ready': 'إشعار جاهزية الجهاز للاستلام', 'delivered': 'وثيقة تسليم الجهاز'}
    title = titles.get(kind, 'وثيقة صيانة')
    filename = f"{device['receipt_no']}_{kind}.png"
    path = os.path.join(DOCUMENTS_DIR, filename)
    img = Image.new('RGB', (1400, 1900), '#f4f7fb')
    draw = ImageDraw.Draw(img)
    navy, teal, gray = '#102a43', '#0b7285', '#334e68'
    draw.rounded_rectangle((45, 45, 1355, 1855), radius=28, fill='white', outline=teal, width=5)
    draw.rectangle((45, 45, 1355, 280), fill=navy)
    draw.text((1270, 90), shop, font=_font(52), fill='white', anchor='ra')
    draw.text((1270, 170), en, font=_font(29, False), fill='#e2edf2', anchor='ra')
    draw.text((1270, 365), title, font=_font(48), fill=navy, anchor='ra')
    draw.text((1270, 440), f"رقم الإيصال: {device['receipt_no']}", font=_font(32), fill=teal, anchor='ra')
    lines = [
        ('اسم العميل', device['owner']), ('رقم الهاتف', device['phone']),
        ('الجهاز', f"{device['brand']} {device['model']}"), ('IMEI / الرقم التسلسلي', device['imei'] or 'غير مسجل'),
        ('الصيانة المطلوبة', device['repair']), ('تاريخ الاستلام', device['received_at'] or device['created_at'])]
    y = 555
    for label, value in lines:
        draw.rounded_rectangle((100, y-42, 1300, y+42), radius=12, fill='#eef5f7')
        draw.text((1250, y), f"{label}: {value}", font=_font(30), fill=gray, anchor='ra')
        y += 105
    if kind == 'received':
        draw.text((1270, y+10), 'نتيجة الفحص عند الاستلام', font=_font(36), fill=navy, anchor='ra'); y += 70
        draw.multiline_text((1250, y), device['checks'], font=_font(25), fill=gray, anchor='ra', align='right', spacing=12)
        y += 210
    messages = {'received': 'تم استلام الجهاز وسيتم التعامل معه بعناية حسب البيانات الموضحة.', 'ready': 'جهازك جاهز للاستلام. يرجى إبراز رقم الإيصال عند الحضور.', 'delivered': 'تم تسليم الجهاز بعد فحص العميل والتأكد من حالته.'}
    draw.rounded_rectangle((100, 1640, 1300, 1770), radius=16, fill='#e2edf2')
    draw.multiline_text((1250, 1705), messages[kind], font=_font(30), fill='#0b5968', anchor='ra', align='right')
    img.save(path, 'PNG')
    return path


def make_document_image_full(device, kind):
    shop = setting('shop_name', 'ترند سنتر الأردن')
    en = setting('shop_en', 'TREND CENTER JORDAN')
    titles = {'received': 'وثيقة استلام جهاز كاملة', 'ready': 'إشعار جاهزية الجهاز للاستلام', 'delivered': 'وثيقة تسليم الجهاز وفحص العميل'}
    title = titles.get(kind, 'وثيقة صيانة')
    checks = [part.strip() for part in (device['checks'] or '').split('،') if part.strip()]
    notes = ('تم فحص الجهاز من قبل العميل ولا توجد أي مشاكل.' if kind == 'delivered' else (device['notes'] or 'لا توجد ملاحظات إضافية'))
    rows = 7 + ((len(checks) + 1) // 2 if kind == 'received' else 0) + 2
    height = max(1900, 720 + rows * 105 + 260)
    path = os.path.join(DOCUMENTS_DIR, f"{device['receipt_no']}_{kind}_full.png")
    img = Image.new('RGB', (1600, height), '#f4f7fa')
    draw = ImageDraw.Draw(img)
    navy, teal, gray = '#102a43', '#0b7285', '#334e68'
    draw.rounded_rectangle((40, 40, 1560, height-40), radius=30, fill='white', outline=teal, width=5)
    draw.rectangle((40, 40, 1560, 290), fill=navy)
    draw.rounded_rectangle((70, 75, 245, 245), radius=28, outline='#d4a72c', width=5)
    draw.text((158, 160), 'TCJ', font=_font(48, False), fill='#d4a72c', anchor='mm')
    draw.text((1480, 90), rtl(shop), font=_font(58), fill='white', anchor='ra')
    draw.text((1480, 175), en, font=_font(31, False), fill='#e2edf2', anchor='ra')
    draw.text((1480, 370), rtl(title), font=_font(50), fill=navy, anchor='ra')
    draw.text((1480, 445), rtl(f"رقم الإيصال: {device['receipt_no']}"), font=_font(32), fill=teal, anchor='ra')
    fields = [('اسم مالك الجهاز', device['owner']), ('رقم الهاتف', device['phone']), ('البراند', device['brand']), ('الموديل', device['model']), ('IMEI / الرقم التسلسلي', device['imei'] or 'غير مسجل'), ('الصيانة المطلوبة', device['repair']), ('تاريخ الاستلام', device['received_at'] or device['created_at'])]
    y = 555
    for label, value in fields:
        draw.rounded_rectangle((100, y-40, 1500, y+40), radius=12, fill='#eef5f7')
        draw.text((1450, y), rtl(f"{label}: {value}"), font=_font(30), fill=gray, anchor='ra')
        y += 100
    if kind == 'received':
        draw.text((1480, y+20), rtl('بنود الفحص قبل الاستلام'), font=_font(38), fill=navy, anchor='ra')
        y += 95
        for i in range(0, len(checks), 2):
            pair = checks[i:i+2]
            for col, item in enumerate(pair):
                x1 = 100 + col * 710
                x2 = x1 + 680
                draw.rounded_rectangle((x1, y-34, x2, y+34), radius=10, fill='#e6f1f4')
                draw.text((x2-20, y), rtl(item), font=_font(25), fill=gray, anchor='ra')
            y += 82
        y += 20
    draw.text((1480, y+10), rtl('ملاحظات إضافية'), font=_font(35), fill=navy, anchor='ra')
    y += 65
    draw.rounded_rectangle((100, y, 1500, y+150), radius=12, fill='#fbfdff', outline='#c8d6df', width=2)
    draw.multiline_text((1450, y+30), rtl(notes), font=_font(27), fill=gray, anchor='ra', align='right', spacing=8)
    footer_y = height - 220
    messages = {'received': 'تم استلام الجهاز بعد تسجيل كامل البيانات وفحص الحالة الظاهر في هذه الوثيقة.', 'ready': 'جهازك جاهز للاستلام. يرجى إبراز رقم الإيصال عند الحضور.', 'delivered': 'تم تسليم الجهاز بعد فحص العميل والتأكد من حالته.'}
    draw.rounded_rectangle((100, footer_y, 1500, footer_y+120), radius=16, fill='#e2edf2')
    draw.multiline_text((1450, footer_y+60), rtl(messages[kind]), font=_font(30), fill='#0b5968', anchor='ra', align='right')
    img.save(path, 'PNG')
    return path


def send_whatsapp(phone, text, image_path=None):
    phone=''.join(c for c in phone if c.isdigit() or c=='+').replace('+','')
    if phone.startswith('00'): phone=phone[2:]
    url='https://web.whatsapp.com/send?phone='+phone+'&text='+urllib.parse.quote(text)
    def worker():
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                context=p.chromium.launch_persistent_context(WHATSAPP_DIR, headless=False)
                page=context.pages[0] if context.pages else context.new_page(); page.goto(url, wait_until='domcontentloaded'); page.wait_for_timeout(6000)
                if image_path and os.path.exists(image_path):
                    file_input = page.locator('input[type="file"]').last
                    file_input.set_input_files(image_path)
                    page.wait_for_timeout(2500)
                    page.keyboard.press('Enter')
                else:
                    page.keyboard.press('Enter')
                page.wait_for_timeout(3500); context.close()
        except Exception:
            webbrowser.open(url)
    threading.Thread(target=worker, daemon=True).start()

def msg(device, kind):
    shop=setting('shop_name','ترند سنتر الأردن'); en=setting('shop_en','TREND CENTER JORDAN'); no=device['receipt_no']
    if kind=='received': return f"{shop} | {en}\nإيصال استلام جهاز رقم: {no}\nالعميل: {device['owner']}\nالجهاز: {device['brand']} {device['model']}\nالصيانة المطلوبة: {device['repair']}\nتاريخ الاستلام: {device['received_at']}\nنحتفظ بالجهاز للعناية والصيانة حسب البيانات أعلاه."
    if kind=='ready': return f"{shop} | {en}\nعزيزي/عزيزتي {device['owner']}، جهازك {device['brand']} {device['model']} أصبح جاهزاً للاستلام.\nرقم الإيصال: {no}\nيرجى إبراز رقم الإيصال عند الحضور."
    return f"{shop} | {en}\nتم تسليم جهاز {device['brand']} {device['model']} للعميل {device['owner']} بعد فحصه واستلامه.\nرقم الإيصال: {no}\nشكراً لثقتكم بنا."

@app.route('/catalog', methods=['GET', 'POST'])
def catalog():
    con = db()
    if request.method == 'POST':
        brand = request.form.get('brand','').strip()
        model = request.form.get('model','').strip()
        image = request.files.get('image')
        if not brand or not model:
            flash('يرجى إدخال البراند والموديل.')
        else:
            filename = ''
            if image and image.filename:
                ext = os.path.splitext(image.filename)[1].lower()
                if ext in ('.png', '.jpg', '.jpeg', '.webp'):
                    filename = safe_filename(f'{brand}_{model}') + ext
                    image.save(os.path.join(CATALOG_DIR, filename))
            con.execute('INSERT INTO device_catalog(brand,model,image_filename,created_at) VALUES(?,?,?,?)', (brand, model, filename, datetime.now().strftime('%Y-%m-%d %H:%M')))
            con.commit(); flash('تمت إضافة الموديل إلى الكتالوج المحلي.')
        con.close(); return redirect(url_for('catalog'))
    rows = con.execute('SELECT * FROM device_catalog ORDER BY brand, model').fetchall(); con.close()
    body = render_template_string('''<div class="card"><h2>كتالوج البراندات والموديلات</h2><p class="muted">هذا الكتالوج محلي ويمكنك تحديثه يدويًا دون إنترنت.</p><form method="post" enctype="multipart/form-data"><div class="grid"><div><label>البراند *</label><input name="brand" required placeholder="Apple / Samsung"></div><div><label>الموديل *</label><input name="model" required placeholder="iPhone 15 Pro"></div><div><label>صورة الجهاز</label><input type="file" name="image" accept=".png,.jpg,.jpeg,.webp"></div><div style="align-self:end"><button class="btn green" type="submit">إضافة إلى الكتالوج</button></div></div></form></div><div class="card"><h2>الموديلات المسجلة ({{rows|length}})</h2><table><tr><th>الصورة</th><th>البراند</th><th>الموديل</th><th>الإجراء</th></tr>{% for r in rows %}<tr><td>{% if r.image_filename %}<img src="{{url_for('catalog_image',filename=r.image_filename)}}" style="width:52px;height:52px;object-fit:contain">{% else %}<span class="muted">بدون صورة</span>{% endif %}</td><td>{{r.brand}}</td><td>{{r.model}}</td><td><a class="btn red" href="{{url_for('catalog_delete',id=r.id)}}">حذف</a></td></tr>{% else %}<tr><td colspan="4">لا توجد موديلات بعد.</td></tr>{% endfor %}</table></div>''', rows=rows)
    return render_template_string(DASH_BASE,title='كتالوج الأجهزة',body=body)

@app.route('/catalog/image/<path:filename>')
def catalog_image(filename):
    return send_file(os.path.join(CATALOG_DIR, filename))

@app.route('/catalog/delete/<int:id>')
def catalog_delete(id):
    con=db(); row=con.execute('SELECT image_filename FROM device_catalog WHERE id=?',(id,)).fetchone()
    if row and row['image_filename']:
        try: os.remove(os.path.join(CATALOG_DIR,row['image_filename']))
        except OSError: pass
    con.execute('DELETE FROM device_catalog WHERE id=?',(id,)); con.commit(); con.close(); flash('تم حذف الموديل من الكتالوج.'); return redirect(url_for('catalog'))

@app.route('/')
def home():
    q=request.args.get('q',''); con=db()
    total=con.execute('SELECT COUNT(*) c FROM devices').fetchone()['c']; received=con.execute("SELECT COUNT(*) c FROM devices WHERE status='مستلم'").fetchone()['c']; ready_count=con.execute("SELECT COUNT(*) c FROM devices WHERE status='جاهز للاستلام'").fetchone()['c']; delivered=con.execute("SELECT COUNT(*) c FROM devices WHERE status='تم التسليم'").fetchone()['c']
    rows=con.execute('''SELECT d.*, c.image_filename FROM devices d LEFT JOIN device_catalog c ON c.brand=d.brand AND c.model=d.model WHERE d.owner LIKE ? OR d.phone LIKE ? OR d.receipt_no LIKE ? ORDER BY d.id DESC LIMIT 6''',(f'%{q}%',f'%{q}%',f'%{q}%')).fetchall(); con.close()
    body=render_template_string('''<div class="top"><div><h1>لوحة التحكم</h1><small>نظرة شاملة على عمليات الصيانة والاستلام اليوم</small></div><a class="btn gold" href="{{url_for('new_device')}}">+ استلام جهاز جديد</a></div><div class="stats"><div class="stat"><span>إجمالي الأجهزة</span><div class="n">{{total}}</div><small class="muted">جهاز مسجل</small></div><div class="stat gold"><span>قيد الإصلاح</span><div class="n">{{received}}</div><small class="muted">جهاز يحتاج متابعة</small></div><div class="stat"><span>جاهزة للاستلام</span><div class="n">{{ready_count}}</div><small class="muted">بانتظار العميل</small></div><div class="stat gold"><span>تم التسليم</span><div class="n">{{delivered}}</div><small class="muted">عملية مكتملة</small></div></div><div class="dashboard"><section class="panel"><h2>أحدث الأجهزة <span class="muted">({{rows|length}})</span></h2>{% for d in rows %}<div class="device-card"><div><div class="model">{{d.brand}} {{d.model}}</div><div class="meta">{{d.owner}} · {{d.receipt_no}}</div><div style="margin-top:7px"><span class="pill {% if d.status=='مستلم' %}gold{% endif %}">{{d.status}}</span></div></div>{% if d.image_filename %}<img class="thumb" src="{{url_for('catalog_image',filename=d.image_filename)}}">{% else %}<div class="thumb"></div>{% endif %}</div>{% else %}<p class="muted">لا توجد أجهزة مسجلة بعد.</p>{% endfor %}<a class="btn" href="{{url_for('home')}}">عرض كل الأجهزة</a></section><section class="panel"><h2>حالة الإصلاح</h2><div class="timeline"><div class="step"><span class="dot"></span><strong>استلام الجهاز</strong><div class="muted">تم تسجيل بيانات العميل والفحص الأولي</div></div><div class="step current"><span class="dot"></span><strong>قيد الإصلاح</strong><div class="muted">متابعة الأجهزة التي ما زالت في الصيانة</div></div><div class="step"><span class="dot"></span><strong>اختبار الجهاز</strong><div class="muted">فحص نهائي قبل الإشعار بالجاهزية</div></div><div class="step"><span class="dot"></span><strong>جاهز للاستلام</strong><div class="muted">إرسال إشعار واتساب للعميل</div></div></div></section><section class="panel"><h2>استلام جهاز جديد</h2><p class="muted">ابدأ تسجيل العميل والجهاز والفحص من نموذج الاستلام الكامل.</p><div class="formgrid"><div><label>اسم العميل</label><input placeholder="أدخل اسم العميل" readonly></div><div><label>رقم الهاتف</label><input placeholder="9627xxxxxxxx" readonly></div><div><label>البراند والموديل</label><input placeholder="اختر من الكتالوج المحلي" readonly></div><div><label>الصيانة المطلوبة</label><input placeholder="وصف العطل" readonly></div><div class="wide"><label>الفحص الأولي</label><div class="checksmini">{% for c in ['الشاشة','اللمس','الكاميرا','الشحن','البطارية','الاتصال'] %}<span>✓ {{c}}</span>{% endfor %}</div></div></div><div class="actions"><a class="btn gold" href="{{url_for('new_device')}}">حفظ واستلام الجهاز</a><a class="btn" href="{{url_for('catalog')}}">إدارة الكتالوج</a></div></section></div>''',total=total,received=received,ready_count=ready_count,delivered=delivered,rows=rows)
    return render_template_string(DASH_BASE,title='لوحة التحكم',body=body)

@app.route('/new',methods=['GET','POST'])
def new_device():
    if request.method=='POST':
        now=datetime.now().strftime('%Y-%m-%d %H:%M'); con=db(); count=con.execute('SELECT COUNT(*) c FROM devices').fetchone()['c']+1; no=f'TCJ-{datetime.now():%Y%m%d}-{count:04d}'
        checks='، '.join(f'{x}: {request.form.get("check_"+str(i),"غير مفحوص")}' for i,x in enumerate(CHECKS)); vals=(no,now,request.form['owner'],request.form['phone'],request.form['brand'],request.form['model'],request.form.get('imei',''),request.form['repair'],checks,request.form.get('notes',''),'مستلم',now,None,None)
        cur=con.execute('INSERT INTO devices(receipt_no,created_at,owner,phone,brand,model,imei,repair,checks,notes,status,received_at,ready_at,delivered_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',vals); did=cur.lastrowid; con.commit(); d=con.execute('SELECT * FROM devices WHERE id=?',(did,)).fetchone(); con.close(); image_path=make_document_image_full(d, 'received'); save_document_to_desktop(d, 'received', image_path); send_whatsapp(d['phone'],msg(d,'received'),image_path); flash('تم إنشاء وثيقة الاستلام كصورة وفتح واتساب لإرسالها للعميل.'); return redirect(url_for('device',id=did))
    con=db(); catalog_rows=con.execute('SELECT * FROM device_catalog ORDER BY brand, model').fetchall(); con.close()
    brands=sorted({r['brand'] for r in catalog_rows}); models=sorted({r['model'] for r in catalog_rows})
    body=render_template_string('''<div class="card"><h2>استلام جهاز جديد</h2><p class="muted">أكمل الفحص قبل الضغط على تأكيد الاستلام. يمكنك اختيار البراند والموديل من الكتالوج المحلي أو كتابة قيمة جديدة.</p><form method="post"><div class="grid"><div><label>اسم مالك الجهاز *</label><input name="owner" required></div><div><label>رقم الهاتف مع رمز الدولة *</label><input name="phone" placeholder="9627xxxxxxxx" required></div><div><label>البراند *</label><input name="brand" list="brand-list" required placeholder="Apple / Samsung"><datalist id="brand-list">{% for b in brands %}<option value="{{b}}">{% endfor %}</datalist></div><div><label>الموديل *</label><input name="model" list="model-list" required placeholder="iPhone 13"><datalist id="model-list">{% for m in models %}<option value="{{m}}">{% endfor %}</datalist></div><div><label>IMEI / الرقم التسلسلي</label><input name="imei"></div><div class="wide"><label>الصيانة المطلوبة *</label><textarea name="repair" required></textarea></div><div class="full"><label>بنود الفحص</label><div class="checks">{% for c in checks %}<div class="check"><input type="text" name="check_{{loop.index0}}" value="سليم">{{c}}</div>{% endfor %}</div></div><div class="full"><label>ملاحظات إضافية</label><textarea name="notes"></textarea></div></div><br><button class="btn green" type="submit">تأكيد الاستلام وإرسال الوثيقة عبر واتساب</button></form></div>''',checks=CHECKS,brands=brands,models=models)
    return render_template_string(DASH_BASE,title='استلام جهاز',body=body)

@app.route('/device/<int:id>')
def device(id):
    con=db(); d=con.execute('SELECT * FROM devices WHERE id=?',(id,)).fetchone(); con.close()
    if not d: return redirect(url_for('home'))
    body=render_template_string('''<div class="card"><h2>تفاصيل الجهاز {{d.receipt_no}}</h2><div class="grid"><div><label>العميل</label><input readonly value="{{d.owner}}"></div><div><label>الهاتف</label><input readonly value="{{d.phone}}"></div><div><label>الجهاز</label><input readonly value="{{d.brand}} {{d.model}}"></div><div><label>IMEI</label><input readonly value="{{d.imei}}"></div><div class="wide"><label>الصيانة المطلوبة</label><textarea readonly>{{d.repair}}</textarea></div><div class="full"><label>الفحص</label><textarea readonly>{{d.checks}}</textarea></div><div class="full"><label>الملاحظات</label><textarea readonly>{{d.notes}}</textarea></div></div><br><div class="actions"><a class="btn secondary" href="{{url_for('home')}}">رجوع</a>{% if d.status=='مستلم' %}<a class="btn orange" href="{{url_for('ready',id=d.id)}}">الجهاز جاهز للاستلام</a>{% elif d.status=='جاهز للاستلام' %}<a class="btn green" href="{{url_for('deliver',id=d.id)}}">تأكيد استلام العميل للجهاز</a>{% endif %}<a class="btn" href="{{url_for('resend',id=d.id,kind='received')}}">إعادة إرسال الاستلام</a><a class="btn secondary" href="{{url_for('document_file',id=d.id,kind='received')}}">تنزيل وثيقة الاستلام PNG</a>{% if d.status=='جاهز للاستلام' %}<a class="btn secondary" href="{{url_for('document_file',id=d.id,kind='ready')}}">تنزيل وثيقة الجاهزية PNG</a>{% elif d.status=='تم التسليم' %}<a class="btn secondary" href="{{url_for('document_file',id=d.id,kind='delivered')}}">تنزيل وثيقة التسليم PNG</a>{% endif %}</div></div>''',d=d)
    return render_template_string(DASH_BASE,title='تفاصيل الجهاز',body=body)

@app.route('/ready/<int:id>')
def ready(id):
    con=db(); now=datetime.now().strftime('%Y-%m-%d %H:%M'); con.execute("UPDATE devices SET status='جاهز للاستلام',ready_at=? WHERE id=?",(now,id)); d=con.execute('SELECT * FROM devices WHERE id=?',(id,)).fetchone(); con.commit(); con.close(); image_path=make_document_image_full(d, 'ready'); save_document_to_desktop(d, 'ready', image_path); send_whatsapp(d['phone'],msg(d,'ready'),image_path); flash('تم إنشاء إشعار الجاهزية كصورة وفتح واتساب لإرساله للعميل.'); return redirect(url_for('device',id=id))

@app.route('/deliver/<int:id>')
def deliver(id):
    con=db(); now=datetime.now().strftime('%Y-%m-%d %H:%M'); con.execute("UPDATE devices SET status='تم التسليم',delivered_at=? WHERE id=?",(now,id)); d=con.execute('SELECT * FROM devices WHERE id=?',(id,)).fetchone(); con.commit(); con.close(); image_path=make_document_image_full(d, 'delivered'); save_document_to_desktop(d, 'delivered', image_path); send_whatsapp(d['phone'],msg(d,'delivered'),image_path); flash('تم إنشاء وثيقة التسليم كصورة وفتح واتساب لإرسالها للعميل.'); return redirect(url_for('device',id=id))

@app.route('/resend/<int:id>/<kind>')
def resend(id,kind):
    con=db(); d=con.execute('SELECT * FROM devices WHERE id=?',(id,)).fetchone(); con.close(); image_path=make_document_image_full(d, kind); save_document_to_desktop(d, kind, image_path); send_whatsapp(d['phone'],msg(d,kind),image_path); flash('تم إنشاء الصورة وفتح واتساب لإعادة إرسال الوثيقة.'); return redirect(url_for('device',id=id))

@app.route('/document/<int:id>/<kind>')
def document_file(id, kind):
    if kind not in ('received', 'ready', 'delivered'):
        return redirect(url_for('home'))
    con= db(); d = con.execute('SELECT * FROM devices WHERE id=?', (id,)).fetchone(); con.close()
    if not d:
        return redirect(url_for('home'))
    path = make_document_image_full(d, kind)
    save_document_to_desktop(d, kind, path)
    return send_file(path, mimetype='image/png', as_attachment=True, download_name=os.path.basename(path))


@app.route('/customers')
def customers():
    con=db(); rows=con.execute('SELECT owner,phone,COUNT(*) total,MAX(created_at) last_visit FROM devices GROUP BY owner,phone ORDER BY last_visit DESC').fetchall(); con.close()
    body=render_template_string('''<div class="card"><h2>العملاء</h2><p class="muted">سجل العملاء وعدد الأجهزة المسجلة لكل عميل.</p><table><tr><th>العميل</th><th>الهاتف</th><th>عدد الأجهزة</th><th>آخر زيارة</th></tr>{% for r in rows %}<tr><td>{{r.owner}}</td><td>{{r.phone}}</td><td>{{r.total}}</td><td>{{r.last_visit}}</td></tr>{% else %}<tr><td colspan="4">لا يوجد عملاء بعد.</td></tr>{% endfor %}</table></div>''',rows=rows)
    return render_template_string(DASH_BASE,title='العملاء',body=body)

@app.route('/reports')
def reports():
    con=db(); by_status=con.execute('SELECT status,COUNT(*) total FROM devices GROUP BY status').fetchall(); by_brand=con.execute('SELECT brand,COUNT(*) total FROM devices GROUP BY brand ORDER BY total DESC').fetchall(); con.close()
    body=render_template_string('''<div class="card"><h2>التقارير</h2><p class="muted">ملخص حالة الأجهزة وتوزيعها حسب البراند.</p><div class="grid"><div><h3>حسب الحالة</h3><table><tr><th>الحالة</th><th>العدد</th></tr>{% for r in by_status %}<tr><td>{{r.status}}</td><td>{{r.total}}</td></tr>{% else %}<tr><td colspan="2">لا توجد بيانات.</td></tr>{% endfor %}</table></div><div><h3>حسب البراند</h3><table><tr><th>البراند</th><th>العدد</th></tr>{% for r in by_brand %}<tr><td>{{r.brand}}</td><td>{{r.total}}</td></tr>{% else %}<tr><td colspan="2">لا توجد بيانات.</td></tr>{% endfor %}</table></div></div></div>''',by_status=by_status,by_brand=by_brand)
    return render_template_string(DASH_BASE,title='التقارير',body=body)

@app.route('/settings',methods=['GET','POST'])
def settings():
    if request.method=='POST':
        con=db(); con.execute('INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)',('shop_name',request.form['shop_name'])); con.execute('INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)',('shop_en',request.form['shop_en'])); con.commit(); con.close(); flash('تم حفظ إعدادات المحل.'); return redirect(url_for('settings'))
    body=render_template_string('''<div class="card"><h2>إعدادات المحل</h2><form method="post"><div class="grid"><div><label>اسم المحل بالعربية</label><input name="shop_name" value="{{name}}"></div><div><label>اسم المحل بالإنجليزية</label><input name="shop_en" value="{{en}}" dir="ltr"></div></div><br><button class="btn green">حفظ الإعدادات</button></form><p class="muted">ملاحظة: يجب أن يتضمن رقم العميل رمز الدولة بدون +، مثل 9627xxxxxxxx.</p></div>''',name=setting('shop_name','ترند سنتر الأردن'),en=setting('shop_en','TREND CENTER JORDAN'))
    return render_template_string(DASH_BASE,title='الإعدادات',body=body)

DASH_BASE = '''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{{title}} | TREND CENTER JORDAN</title><style>
*{box-sizing:border-box}body{margin:0;background:#f5f7fa;color:#203040;font-family:Tahoma,Arial,sans-serif;font-weight:700}.app{display:grid;grid-template-columns:1fr 270px;min-height:100vh}.side{grid-column:2;background:#102b3f;color:#fff;padding:26px 18px;display:flex;flex-direction:column;gap:10px}.logo{display:flex;align-items:center;gap:10px;padding:10px 8px 26px;border-bottom:1px solid #315060;margin-bottom:8px}.logo-mark{border:2px solid #d5ad56;color:#d5ad56;border-radius:12px;padding:9px 7px;font-size:18px;letter-spacing:1px}.logo strong{display:block;font-size:18px}.logo small{display:block;color:#b9ced5;font-size:11px;margin-top:5px}.side a{color:#d9e7eb;text-decoration:none;padding:13px 14px;border-radius:12px;display:flex;align-items:center;gap:10px}.side a:hover,.side a.active{background:#0c7d86;color:white}.support{margin-top:auto;background:#0c6975;border-radius:15px;padding:16px;color:#e7f6f7;font-size:12px}.main{grid-column:1;align-self:start;padding:25px 30px;max-width:1550px;width:100%;margin:0 auto;min-height:100vh}.top{display:flex;justify-content:space-between;align-items:center;margin-bottom:22px}.top h1{margin:0;font-size:25px}.top small{color:#718096}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:20px}.stat{background:#fff;border-radius:16px;padding:18px;box-shadow:0 6px 20px #21354712;border-right:5px solid #0b7c86}.stat.gold{border-right-color:#d5ad56}.stat .n{font-size:28px;color:#0b6875;margin-top:8px}.dashboard{display:grid;grid-template-columns:1.1fr 1.2fr 1fr;gap:18px;align-items:start}.panel{background:#fff;border-radius:16px;padding:18px;box-shadow:0 6px 20px #21354712}.panel h2{font-size:18px;margin:0 0 15px}.muted{color:#728391;font-size:12px}.device-card{border:1px solid #e5edf1;border-radius:13px;padding:12px;margin-bottom:10px;display:flex;justify-content:space-between;gap:10px;align-items:center}.device-card .model{font-size:14px}.device-card .meta{font-size:11px;color:#82919b;margin-top:5px}.thumb{width:55px;height:55px;border-radius:12px;background:#eef5f7;object-fit:contain}.pill{display:inline-block;border-radius:20px;padding:5px 9px;font-size:10px;background:#e2f2f3;color:#08717a}.pill.gold{background:#fff1cf;color:#856404}.timeline{position:relative;padding-right:20px}.timeline:before{content:"";position:absolute;right:8px;top:12px;bottom:12px;width:2px;background:#cfe1e6}.step{position:relative;padding:10px 25px 10px 0}.dot{position:absolute;right:0;top:13px;width:17px;height:17px;border-radius:50%;background:#0b7c86;border:3px solid #d5eef0}.step.current{background:#eef8f8;border-radius:10px}.formgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.formgrid label{display:block;font-size:11px;color:#718096;margin-bottom:5px}.formgrid input,.formgrid textarea,.formgrid select{width:100%;border:1px solid #d9e3e8;border-radius:9px;padding:10px;font:inherit;background:#fbfdff}.formgrid textarea{min-height:55px}.checksmini{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:8px}.checksmini span{background:#f0f6f7;border-radius:8px;padding:8px;font-size:10px;text-align:center}.actions{display:flex;gap:8px;margin-top:14px}.btn{border:0;border-radius:9px;padding:10px 14px;background:#0b7c86;color:#fff;text-decoration:none;font:inherit;cursor:pointer}.btn.gold{background:#d5ad56;color:#263746}.wide{grid-column:1/-1}@media(max-width:1100px){.dashboard{grid-template-columns:1fr 1fr}.stats{grid-template-columns:repeat(2,1fr)}}@media(max-width:700px){.app{display:block}.side{display:none}.main{padding:15px}.dashboard{grid-template-columns:1fr}.stats{grid-template-columns:1fr 1fr}.formgrid{grid-template-columns:1fr}}
</style></head><body><div class="app" style="align-items:start;"><aside class="side"><div class="logo"><span class="logo-mark">TCJ</span><div><strong>ترند سنتر الأردن</strong><small>TREND CENTER JORDAN</small></div></div><a href="{{url_for('home')}}" class="active">⌂ الرئيسية</a><a href="{{url_for('home')}}">▣ الأجهزة</a><a href="{{url_for('new_device')}}">⇩ استلام جهاز</a><a href="{{url_for('catalog')}}">▦ الكتالوج</a><a href="{{url_for('settings')}}">⚙ الإعدادات</a><a href="{{url_for('customers')}}">◉ العملاء</a><a href="{{url_for('reports')}}">▤ التقارير</a><div class="support">الدعم الفني<br><strong>واتساب: 0787779095</strong><br><small>خدمة صيانة احترافية</small></div></aside><main class="main">{{body|safe}}</main></div></body></html>'''

init_db()
if __name__=='__main__': app.run(host='127.0.0.1',port=5050,debug=False)
