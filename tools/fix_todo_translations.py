#!/usr/bin/env python3
"""Apply targeted fixes to todoText translations in .env files."""
import json
from pathlib import Path

TASKS_DIR = Path(__file__).resolve().parents[1] / "robot" / "tasks"

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# filename -> {lang: (old_substring, new_substring)}
REPLACEMENTS = {
    "for1.env": {
        "hi": ('"फॉर"', '"for"'),
        "bn": ('"ফর"', '"for"'),
        "el": ('"για"', '"for"'),
        "sv": ('"för"', '"for"'),
        "cs": ('"pro"', '"for"'),
        "tr": ('"For"', '"for"'),
    },
    "forfun1.env": {
        "hi": ('"फॉर"', '"for"'),
        "bn": ('"ফর"', '"for"'),
        "el": ('"για"', '"for"'),
        "sv": ('"för"', '"for"'),
        "cs": ('"pro"', '"for"'),
    },
    "forfun2.env": {
        "sv": ('"för"', '"for"'),
    },
    "forfun3.env": {
        "hi": ('"फॉर"', '"for"'),
        "bn": ('"ফর"', '"for"'),
        "el": ('"για"', '"for"'),
        "sv": ('"för"', '"for"'),
        "cs": ('"pro"', '"for"'),
    },
    "forfun4.env": {
        "hi": ('"फॉर"', '"for"'),
        "bn": ('"ফর"', '"for"'),
        "el": ('"για"', '"for"'),
        "sv": ('"för"', '"for"'),
        "cs": ('"pro"', '"for"'),
    },
    "forfun5.env": {
        "sv": ('"för"', '"for"'),
    },
    "forfun6.env": {
        "sv": ('"för"', '"for"'),
    },
    "forfun7.env": {
        "sv": ('"för"', '"for"'),
    },
    "forfun8.env": {
        "hi": ('"फॉर"', '"for"'),
        "bn": ('"ফর"', '"for"'),
        "el": ('"για"', '"for"'),
        "sv": ('"för"', '"for"'),
        "cs": ('"pro"', '"for"'),
    },
    "forfun9.env": {
        "hi": ('"फॉर"', '"for"'),
        "bn": ('"ফর"', '"for"'),
        "el": ('"για"', '"for"'),
        "sv": ('"för"', '"for"'),
        "cs": ('"pro"', '"for"'),
    },
    "wif9.env": {
        "es": ('"si"', '"if"'),
        "uk": ('«якщо»', '«if»'),
        "be": ('"калі"', '«if»'),
        "el": ('"αν"', '"if"'),
        "sv": ('"om"', '"if"'),
        "cs": ('„pokud“', '„if“'),
        "ro": ('„dacă”', '„if"'),
    },
    "if4.env": {
        "hi": ('"पेंट()"', '"paint()"'),
        "ur": ('"پینٹ()"', '⁦"paint()"⁩'),
    },
    "if1.env": {
        "uk": ('робота', 'Робота'),
        "fr": ('robot', 'Robot'),
        "nl": ('robot', 'Robot'),
        "el": ('ρομπότ', 'Ρομπότ'),
        "cs": ('robota', 'Robota'),
        "sv": ('roboten', 'Roboten'),
        "ro": ('robotul', 'Robotul'),
        "hu": ('robotot', 'Robotot'),
        "de": ('bemalt', 'gefärbt'),
        "it": ('dipinta', 'colorata'),
        "be": ('зафарбаваная', 'пафарбаваная'),
        "ar": ('تم رسم الخلية التي تحتوي على الروبوت', 'كانت الخلية التي تحتوي على الروبوت ملونة'),
    },
    "compound1.env": {
        "it": ('robot', 'Robot'),
        "nl": ('robot', 'Robot'),
        "el": ('ρομπότ', 'Ρομπότ'),
        "cs": ('robota', 'Robota'),
        "sv": ('roboten', 'Roboten'),
        "ro": ('robotul', 'Robotul'),
        "be": ('робата', 'Робата'),
    },
    "fun1.env": {
        "zh-hans": ('创建一个移动 Robot 4 单元的函数。使用4次。', '创建一个让 Robot 移动 4 个单元的函数。使用4次。'),
        "zh-hant": ('建立一個移動 Robot 4 單元的函數。使用4次。', '建立一個讓 Robot 移動 4 個單元的函數。使用4次。'),
        "hi": ('एक फ़ंक्शन बनाएं जो रोबोट 4 कोशिकाओं को स्थानांतरित करता है। इसे 4 बार प्रयोग करें.', 'एक ऐसा फ़ंक्शन बनाएं जो रोबोट को 4 कोशिकाएँ आगे बढ़ाए। इसे 4 बार प्रयोग करें।'),
        "es": ('Crea una función que mueva las celdas del Robot 4. Úselo 4 veces.', 'Crea una función que mueva el Robot 4 celdas. Úsala 4 veces.'),
        "fr": ('Créez une fonction qui déplace les cellules du Robot 4. Utilisez-le 4 fois.', 'Créez une fonction qui déplace le Robot de 4 cellules. Utilisez-la 4 fois.'),
        "ar": ('قم بإنشاء وظيفة تحرك خلايا ⁦Robot⁩ ⁦4⁩. استخدميه ⁦4⁩ مرات.', 'قم بإنشاء وظيفة تحرّك الروبوت ⁦4⁩ خلايا. استخدميها ⁦4⁩ مرات.'),
        "bn": ('একটি ফাংশন তৈরি করুন যা রোবট 4 কোষগুলিকে সরিয়ে দেয়। এটি 4 বার ব্যবহার করুন।', 'একটি ফাংশন তৈরি করুন যা রোবটকে 4 কোষ এগিয়ে নিয়ে যায়। এটি 4 বার ব্যবহার করুন।'),
        "pt": ('Crie uma função que mova as células do Robô 4. Use-o 4 vezes.', 'Crie uma função que mova o Robô 4 células. Use-a 4 vezes.'),
        "ur": ('ایک فنکشن بنائیں جو روبوٹ ⁦4⁩ سیلز کو منتقل کرے۔ اسے ⁦4⁩ بار استعمال کریں۔', 'ایک فنکشن بنائیں جو روبوٹ کو ⁦4⁩ سیلز آگے بڑھائے۔ اسے ⁦4⁩ بار استعمال کریں۔'),
        "uk": ('Створіть функцію, яка переміщує Robot 4 клітинки. Використовуйте 4 рази.', 'Створіть функцію, яка переміщує Робота на 4 клітинки. Використовуйте її 4 рази.'),
        "pl": ('Utwórz funkcję przesuwającą komórki Robota 4. Użyj go 4 razy.', 'Utwórz funkcję, która przesuwa Robota o 4 komórki. Użyj jej 4 razy.'),
        "be": ('Стварыце функцыю, якая перамяшчае робат на 4 клеткі. Выкарыстоўвайце яго 4 разы.', 'Стварыце функцыю, якая перамяшчае Робата на 4 клеткі. Выкарыстоўвайце яе 4 разы.'),
        "ja": ('Robot 4 のセルを移動する関数を作成します。 4回使用します。', 'Robot を 4 セル進める関数を作成します。4回使用します。'),
        "ko": ('Robot 4 셀을 이동하는 함수를 만듭니다. 4번 사용하세요.', 'Robot을 4칸 이동시키는 함수를 만듭니다. 4번 사용하세요.'),
        "de": ('Erstellen Sie eine Funktion, die die Zellen des Roboters 4 bewegt. Benutze es 4 Mal.', 'Erstellen Sie eine Funktion, die den Roboter um 4 Zellen bewegt. Benutzen Sie sie 4 Mal.'),
        "it": ('Crea una funzione che muova le celle del Robot 4. Usalo 4 volte.', 'Crea una funzione che sposti il Robot di 4 celle. Usala 4 volte.'),
        "nl": ('Creëer een functie die de Robot 4 cellen verplaatst. Gebruik het 4 keer.', 'Creëer een functie die de Robot 4 cellen verplaatst. Gebruik deze 4 keer.'),
        "tr": ('Robot 4 hücrelerini hareket ettiren bir fonksiyon oluşturun. 4 kez kullanın.', "Robot'u 4 hücre ileri hareket ettiren bir fonksiyon oluşturun. 4 kez kullanın."),
        "el": ('Δημιουργήστε μια συνάρτηση που μετακινεί τα κελιά του Robot 4. Χρησιμοποιήστε το 4 φορές.', 'Δημιουργήστε μια συνάρτηση που μετακινεί το Robot κατά 4 κελιά. Χρησιμοποιήστε τη 4 φορές.'),
        "cs": ('Vytvořte funkci, která přesune buňky Robota 4. Použijte jej 4krát.', 'Vytvořte funkci, která posune Robota o 4 buňky. Použijte ji 4krát.'),
        "sv": ('Skapa en funktion som flyttar Robot 4-cellerna. Använd den 4 gånger.', 'Skapa en funktion som flyttar Roboten 4 celler. Använd den 4 gånger.'),
        "ro": ('Creați o funcție care mișcă celulele Robot 4. Folosește-l de 4 ori.', 'Creați o funcție care mută Robotul 4 celule. Folosiți-o de 4 ori.'),
        "hu": ('Hozzon létre egy függvényt, amely mozgatja a Robot 4 cellákat. Használja 4 alkalommal.', 'Hozzon létre egy függvényt, amely 4 cellával előrelépteti a Robotot. Használja 4 alkalommal.'),
    },
}

def main():
    updated = 0
    for fname, langs in REPLACEMENTS.items():
        path = TASKS_DIR / fname
        if not path.exists():
            print(f"SKIP: {fname} not found")
            continue
        data = load(path)
        todo = data.get("todoText", {})
        changed = False
        for lang, (old, new) in langs.items():
            text = todo.get(lang, "")
            if old in text:
                todo[lang] = text.replace(old, new)
                changed = True
            else:
                print(f"WARN: {fname} [{lang}] substring not found: {old!r}")
        if changed:
            data["todoText"] = todo
            save(path, data)
            updated += 1
            print(f"UPDATED: {fname}")
    print(f"\nTotal files updated: {updated}")

if __name__ == "__main__":
    main()
