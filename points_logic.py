#!/usr/bin/env python3
"""
points_logic.py — Ball bonus mantiqi (umumiy modul)

Item (badge/car) foizli bonuslari va pet_dog kunlik bonusini hisoblaydi.
Avval `flask_routes_data.py` ichidagi nested funksiyalar edi — endi 3 joydan
(WebApp checkin, bot toggle_, bot done_) import qilinadi (Qoida #10 sinxron).

Sof funksiyalar: `u` (user dict) ni o'zgartiradi, DB ga to'g'ridan-to'g'ri
yozmaydi — chaqiruvchi `save_user` qiladi.
"""

from config import SHOP_BONUS_EFFECTS
from database import add_points_history


def apply_item_bonuses(u, base_points):
    """
    Faol badge va car mahsulotlari asosida ball bonusini qoʻllaydi.
    Stack qilinadi: badge + car foizlari qoʻshiladi (masalan, 12% + 8% = 20%).
    Faqat `points_percent` turidagi mahsulotlar ishlatiladi.
    Agar round natijasida bonus yoʻqolsa, majburiy +1 ball qoʻshiladi
    (foydalanuvchi har doim badge foydasini koʻrsin).
    """
    total_percent = 0
    for field in ("active_badge", "active_car"):
        item_id = u.get(field, "")
        effect = SHOP_BONUS_EFFECTS.get(item_id)
        if effect and effect.get("type") == "points_percent":
            total_percent += effect.get("value", 0)
    if total_percent <= 0:
        return base_points
    # B variant: majburiy minimum +1 kafolat
    boosted = round(base_points * (1 + total_percent / 100))
    return max(boosted, base_points + 1)


def apply_pet_dog_bonus(u, today, is_undo=False):
    """
    pet_dog faol bo'lsa — kunlik BIRINCHI checkin'ga +N ball qo'shimcha.
    N qiymati: SHOP_BONUS_EFFECTS["pet_dog"]["value"] (config dan).
    is_undo=False: DONE holati — agar bugun bonus berilmagan bo'lsa, beriladi.
    is_undo=True:  UNDO holati — agar bugun bonus berilgan bo'lsa, qaytariladi.
    Returns: qo'llanilgan bonus miqdori (0 agar qo'llanmasa).
    """
    if u.get("active_pet", "") != "pet_dog":
        return 0
    effect = SHOP_BONUS_EFFECTS.get("pet_dog")
    if not effect or effect.get("type") != "daily_bonus":
        return 0
    bonus_value = effect.get("value", 0)
    if bonus_value <= 0:
        return 0
    last_bonus_date = u.get("pet_dog_last_bonus_date", "")
    if is_undo:
        # UNDO: agar bugun bonus berilgan bo'lsa, qaytarish
        if last_bonus_date == today:
            _old_pts = u.get("points", 0)
            u["points"] = max(0, _old_pts - bonus_value)
            # Audit #8: history doim -bonus_value (done branch +bonus_value bilan
            # symmetric). Real points clamp himoya alohida — history audit yozuvi
            # to'liq saqlanadi (edge case: reset orasida undo bo'lsa ham).
            add_points_history(u, -bonus_value, today)
            u["pet_dog_last_bonus_date"] = ""
            return bonus_value
        return 0
    else:
        # DONE: agar bugun birinchi marta bo'lsa, bonus berish
        if last_bonus_date != today:
            u["points"] = u.get("points", 0) + bonus_value
            add_points_history(u, bonus_value, today)
            u["pet_dog_last_bonus_date"] = today
            return bonus_value
        return 0
