from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import ContactMessage, Feature, FAQ, BotJavob, Soha
import requests
import json
import uuid
import re


def index(request):
    features = Feature.objects.filter(faol=True)
    faqs = FAQ.objects.filter(faol=True)
    sohalar = Soha.objects.filter(faol=True)
    return render(request, 'main/index.html', {
        'features': features,
        'faqs': faqs,
        'sohalar': sohalar,
    })


@csrf_exempt
def send_contact(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ism = data.get('ism', '').strip()
            telefon = data.get('telefon', '').strip()
            manzil = data.get('manzil', '').strip()
            xabar = data.get('xabar', '').strip()

            if not ism or not telefon or not manzil:
                return JsonResponse({'ok': False, 'error': "Barcha maydonlarni to'ldiring"})

            # Bazaga saqlash
            msg = ContactMessage.objects.create(
                ism_familiya=ism,
                telefon=telefon,
                manzil=manzil,
                xabar=xabar
            )

            # Telegramga yuborish
            qoshimcha = xabar if xabar else "Yo'q"
            vaqt = timezone.localtime(msg.yaratilgan_vaqt).strftime('%d.%m.%Y, %H:%M')

            text = (
                "🔥 *YANGI BUYURTMA (STARBOR)* 🔥\n\n"
                f"👤 *Mijoz:* {ism}\n"
                f"📞 *Telefon:* {telefon}\n"
                f"📍 *Manzil (Andijon):* {manzil}\n"
                f"💬 *Qo'shimcha:* {qoshimcha}\n"
                f"🕒 *Vaqt:* {vaqt}\n"
                f"✍️ *Javob yozish:* Shu xabar ustiga bosib Reply qiling\n\n"
                f"🆔 *Buyurtma #:* {msg.id}"
            )

            bot_token = settings.TELEGRAM_BOT_TOKEN
            chat_id = settings.TELEGRAM_CHAT_ID
            tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

            requests.post(tg_url, json={
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }, timeout=10)

            return JsonResponse({'ok': True, 'buyurtma_id': msg.id})

        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})

    return JsonResponse({'ok': False, 'error': "Faqat POST so'rov qabul qilinadi"})


@csrf_exempt
def telegram_webhook(request):
    """Telegramdan kelgan xabarlarni qabul qilish"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message', {})
            text = message.get('text', '')
            chat_id = str(message.get('chat', {}).get('id', ''))

            # Faqat sayt egasidan kelgan xabarni qabul qilish
            if chat_id != str(settings.TELEGRAM_CHAT_ID):
                return JsonResponse({'ok': True})

            bot_token = settings.TELEGRAM_BOT_TOKEN
            tg_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

            reply_to = message.get('reply_to_message', {})
            buyurtma_id = None
            javob_matni = ''

            # 1. Reply (javob berish) funksiyasi orqali
            if reply_to and text:
                reply_text = reply_to.get('text', '')
                # Xabardan ID ni qidiramiz
                match = re.search(r"🆔 Buyurtma #: (\d+)", reply_text) or re.search(r"🆔 \*Buyurtma #:\* (\d+)", reply_text)
                if match:
                    buyurtma_id = int(match.group(1))
                    javob_matni = text

            # 2. Eskicha /javob_1 formatida yozilsa
            elif text.startswith('/javob_'):
                parts = text.split(' ', 1)
                try:
                    buyurtma_id = int(parts[0].replace('/javob_', ''))
                    javob_matni = parts[1] if len(parts) > 1 else ''
                except ValueError:
                    pass

            # Agar buyurtma ID topilgan bo'lsa
            if buyurtma_id is not None:
                try:
                    buyurtma = ContactMessage.objects.get(id=buyurtma_id)

                    if javob_matni:
                        # Javobni bazaga saqlash
                        BotJavob.objects.create(
                            buyurtma=buyurtma,
                            matn=javob_matni
                        )

                        # Siz (egaga) tasdiqlash xabari
                        requests.post(tg_url, json={
                            'chat_id': chat_id,
                            'text': f"✅ Javob #{buyurtma_id} ({buyurtma.ism_familiya}) ga yuborildi!",
                        }, timeout=10)
                    else:
                        requests.post(tg_url, json={
                            'chat_id': chat_id,
                            'text': f"❌ Javob matni yozing! (Buyurtma #{buyurtma_id})",
                        }, timeout=10)

                except ContactMessage.DoesNotExist:
                    requests.post(tg_url, json={
                        'chat_id': chat_id,
                        'text': f"❌ #{buyurtma_id} raqamli buyurtma topilmadi!",
                    }, timeout=10)

        except Exception as e:
            pass

    return JsonResponse({'ok': True})


def javob_olish(request, buyurtma_id):
    """Mijoz saytdan javob tekshiradi (polling)"""
    try:
        buyurtma = ContactMessage.objects.get(id=buyurtma_id)
        javoblar = BotJavob.objects.filter(buyurtma=buyurtma, korildi=False)

        javob_list = []
        for j in javoblar:
            javob_list.append({
                'matn': j.matn,
                'vaqt': timezone.localtime(j.vaqt).strftime('%H:%M')
            })
            j.korildi = True
            j.save()

        return JsonResponse({'ok': True, 'javoblar': javob_list})

    except ContactMessage.DoesNotExist:
        return JsonResponse({'ok': False, 'javoblar': []})


def google_verification(request):
    return HttpResponse("google-site-verification: googleec6e8bba19eb9bcf.html", content_type="text/plain")
