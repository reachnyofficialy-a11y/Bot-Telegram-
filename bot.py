import json
import os
import uuid
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import keep_alive

TOKEN = os.environ.get(
    "BOT_TOKEN", "9145599477:AAHw0tySw95Tx0XD9klPKqN4wIkLOTEFQio"
)
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8413684077"))
KHQR_PATH = os.environ.get("KHQR_PATH", "IMG_1813.jpeg")

with open("catalog.json", "r", encoding="utf-8") as f:
  CATALOG = json.load(f)

ORDERS = {}
PENDING_RECEIPT_USER = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  keyboard = [
      [
          InlineKeyboardButton(
              f"{item['name']} - ${item['price_usd']:.0f}",
              callback_data=f"buy:{skin_id}",
          )
      ]
      for skin_id, item in CATALOG.items()
  ]

  # Keyboard Line ថ្មី ១ ជួរនៅខាងក្រោម
  keyboard.append([
      InlineKeyboardButton("ℹ️ របៀបទិញ", callback_data="how_to_buy"),
      InlineKeyboardButton("📩 Admin", url=f"tg://user?id={ADMIN_ID}"),
  ])

  await update.message.reply_text(
      "សូមជ្រើសរើស Skin Script ($1 / skin):",
      reply_markup=InlineKeyboardMarkup(keyboard),
  )


async def on_how_to_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  await query.message.reply_text(
      "1. ជ្រើសរើស Skin Script ($1)\n"
      "2. ស្កេន KHQR រួចផ្ញើរូបភាព Receipt ចូល Bot\n"
      "3. រង់ចាំ Admin Approve ដើម្បីទទួលបាន File Script"
  )


async def on_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()

  skin_id = query.data.split(":", 1)[1]
  item = CATALOG.get(skin_id)
  if not item:
    await query.message.reply_text("រកមិនឃើញ Skin នេះទេ។")
    return

  user = query.from_user
  order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

  ORDERS[order_id] = {
      "order_id": order_id,
      "user_id": user.id,
      "username": user.username or user.full_name,
      "skin_id": skin_id,
      "skin_name": item["name"],
      "price_usd": item["price_usd"],
      "file_path": item["file_path"],
      "status": "WAITING_RECEIPT",
  }
  PENDING_RECEIPT_USER[user.id] = order_id

  caption = (
      f"🧾 Order ID: `{order_id}`\n"
      f"🎮 Skin: {item['name']}\n"
      f"💵 តម្លៃ: ${item['price_usd']:.0f}\n\n"
      "សូមស្កេន KHQR ដើម្បីបង់ប្រាក់ រួចផ្ញើរូបភាព Receipt ចូលក្នុង Bot នេះ។"
  )

  if os.path.exists(KHQR_PATH):
    with open(KHQR_PATH, "rb") as photo:
      await query.message.reply_photo(
          photo=photo, caption=caption, parse_mode="Markdown"
      )
  else:
    await query.message.reply_text(caption, parse_mode="Markdown")


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user = update.effective_user
  order_id = PENDING_RECEIPT_USER.get(user.id)

  if not order_id or order_id not in ORDERS:
    await update.message.reply_text(
        "សូមចុចជ្រើសរើស Skin Script ជាមុនសិន មុនពេលផ្ញើ Receipt។"
    )
    return

  order = ORDERS[order_id]
  order["status"] = "PENDING_ADMIN"
  photo = update.message.photo[-1]

  admin_keyboard = InlineKeyboardMarkup([[
      InlineKeyboardButton(
          "✅ Approve & Send Script", callback_data=f"approve:{order_id}"
      ),
      InlineKeyboardButton("❌ Reject", callback_data=f"reject:{order_id}"),
  ]])

  admin_caption = (
      f"📥 Receipt ថ្មីសម្រាប់ពិនិត្យ\n"
      f"• Order ID: `{order_id}`\n"
      f"• អ្នកទិញ: @{user.username} ({user.id})\n" if user.username else ""
  )
  if not user.username:
    admin_caption = (
        f"📥 Receipt ថ្មីសម្រាប់ពិនិត្យ\n"
        f"• Order ID: `{order_id}`\n"
        f"• អ្នកទិញ: {user.full_name} (`{user.id}`)\n"
    )
  else:
    admin_caption = (
        f"📥 Receipt ថ្មីសម្រាប់ពិនិត្យ\n"
        f"• Order ID: `{order_id}`\n"
        f"• អ្នកទិញ: @{user.username} (`{user.id}`)\n"
    )

  admin_caption += (
      f"• Skin: {order['skin_name']}\n" f"• តម្លៃ: ${order['price_usd']:.0f}"
  )

  await context.bot.send_photo(
      chat_id=ADMIN_ID,
      photo=photo.file_id,
      caption=admin_caption,
      parse_mode="Markdown",
      reply_markup=admin_keyboard,
  )

  await update.message.reply_text(
      f"✅ បានទទួល Receipt សម្រាប់ Order `{order_id}` រួចរាល់។ សូមរង់ចាំ Admin ផ្ទៀងផ្ទាត់។",
      parse_mode="Markdown",
  )


async def on_admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()

  if query.from_user.id != ADMIN_ID:
    await query.message.reply_text("អ្នកមិនមែនជា Admin ទេ។")
    return

  action, order_id = query.data.split(":", 1)
  order = ORDERS.get(order_id)

  if not order:
    await query.edit_message_caption(
        caption=(query.message.caption or "")
        + "\n\n⚠️ រកមិនឃើញ Order នេះទេ។"
    )
    return

  if order["status"] != "PENDING_ADMIN":
    await query.edit_message_caption(
        caption=(query.message.caption or "")
        + f"\n\nℹ️ Order នេះត្រូវបានចាត់ការរួចហើយ ({order['status']})។"
    )
    return

  if action == "approve":
    file_path = order["file_path"]
    if not os.path.exists(file_path):
      await query.message.reply_text(f"❌ រកមិនឃើញ File នៅលើ Server: `{file_path}`")
      return

    order["status"] = "APPROVED"
    PENDING_RECEIPT_USER.pop(order["user_id"], None)

    with open(file_path, "rb") as doc:
      await context.bot.send_document(
          chat_id=order["user_id"],
          document=doc,
          caption=(
              f"🎉 ការទូទាត់សម្រាប់ Order `{order_id}` ត្រូវបាន Approve!\n"
              f"នេះគឺជា File Script សម្រាប់ **{order['skin_name']}**។"
          ),
          parse_mode="Markdown",
      )

    await query.edit_message_caption(
        caption=(query.message.caption or "") + "\n\n✅ APPROVED & SENT"
    )

  elif action == "reject":
    order["status"] = "REJECTED"
    PENDING_RECEIPT_USER.pop(order["user_id"], None)

    await context.bot.send_message(
        chat_id=order["user_id"],
        text=(
            f"❌ Order `{order_id}` ត្រូវបាន Reject។\n"
            "សូមពិនិត្យការទូទាត់ ឬទាក់ទង Admin ដើម្បីជំនួយ។"
        ),
        parse_mode="Markdown",
    )

    await query.edit_message_caption(
        caption=(query.message.caption or "") + "\n\n❌ REJECTED"
    )


def main():
  keep_alive.keep_alive()
  app = ApplicationBuilder().token(TOKEN).build()

  app.add_handler(CommandHandler("start", start))
  app.add_handler(CallbackQueryHandler(on_how_to_buy, pattern=r"^how_to_buy$"))
  app.add_handler(CallbackQueryHandler(on_buy, pattern=r"^buy:"))
  app.add_handler(MessageHandler(filters.PHOTO, on_photo))
  app.add_handler(
      CallbackQueryHandler(on_admin_decision, pattern=r"^(approve|reject):")
  )

  app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
  main()
