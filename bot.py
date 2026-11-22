import json
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from keep_alive import keep_alive

TOKEN = os.environ.get("9145599477:AAHw0tySw95Tx0XD9klPKqN4wIkLOTEFQio")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8413684077"))
KHQR_PATH = os.environ.get("KHQR_PATH", "khqr.png")

with open("catalog.json", "r", encoding="utf-8") as f:
  CATALOG = json.load(f)

ORDERS = {}


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
  await update.message.reply_text(
      "សូមជ្រើសរើស Skin Script ($1 / skin):",
      reply_markup=InlineKeyboardMarkup(keyboard),
  )


async def on_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()

  skin_id = query.data.split(":", 1)[1]
  skin = CATALOG.get(skin_id)
  if not skin:
    await query.edit_message_text("រកមិនឃើញមុខទំនិញនេះទេ។")
    return

  user_id = query.from_user.id
  order_id = f"ORD-{user_id}-{len(ORDERS) + 1}"
  ORDERS[order_id] = {
      "user_id": user_id,
      "username": query.from_user.username or query.from_user.full_name,
      "skin_id": skin_id,
      "status": "WAITING_RECEIPT",
  }
  context.user_data["active_order_id"] = order_id

  caption = (
      f"🛒 Order: `{order_id}`\n"
      f"🎮 Skin: *{skin['name']}*\n"
      f"💵 តម្លៃ: *${skin['price_usd']:.0f}*\n\n"
      f"សូមស្កេន KHQR ខាងលើដើម្បីបង់ប្រាក់ រួចផ្ញើ **រូបភាព Receipt** ចូលក្នុង Bot នេះ។"
  )
  if os.path.exists(KHQR_PATH):
    with open(KHQR_PATH, "rb") as qr:
      await query.message.reply_photo(
          photo=qr, caption=caption, parse_mode="Markdown"
      )
  else:
    await query.message.reply_text(
        caption + "\n*(កំណត់ KHQR_PATH ដើម្បីបង្ហាញរូប QR)*",
        parse_mode="Markdown",
    )


async def on_receipt_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
  order_id = context.user_data.get("active_order_id")
  if not order_id or order_id not in ORDERS:
    await update.message.reply_text(
        "សូមជ្រើសរើស Skin Script ជាមុនសិនដោយប្រើ /start។"
    )
    return

  order = ORDERS[order_id]
  skin = CATALOG[order["skin_id"]]
  photo_file_id = update.message.photo[-1].file_id

  admin_keyboard = InlineKeyboardMarkup([[
      InlineKeyboardButton(
          "✅ Approve & Send Script", callback_data=f"approve:{order_id}"
      ),
      InlineKeyboardButton("❌ Reject", callback_data=f"reject:{order_id}"),
  ]])

  await context.bot.send_photo(
      chat_id=ADMIN_ID,
      photo=photo_file_id,
      caption=(
          f"📩 Receipt ថ្មីសម្រាប់ Order `{order_id}`\n"
          f"👤 អ្នកទិញ: @{order['username']} (`{order['user_id']}`)\n"
          f"🎮 Skin: *{skin['name']}* (${skin['price_usd']:.0f})"
      ),
      parse_mode="Markdown",
      reply_markup=admin_keyboard,
  )
  await update.message.reply_text(
      "✅ បានទទួល Receipt រួចរាល់។ សូមរង់ចាំ Admin ផ្ទៀងផ្ទាត់ និងអនុម័ត។"
  )


async def on_admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  if query.from_user.id != ADMIN_ID:
    await query.answer("សម្រាប់ Admin ប៉ុណ្ណោះ។", show_alert=True)
    return

  await query.answer()
  action, order_id = query.data.split(":", 1)
  order = ORDERS.get(order_id)
  if not order:
    await query.edit_message_caption(
        caption=(query.caption or "") + "\n\n⚠️ Order នេះត្រូវបានដោះស្រាយរួចហើយ។"
    )
    return

  skin = CATALOG[order["skin_id"]]
  buyer_id = order["user_id"]

  if action == "approve":
    file_path = skin["file_path"]
    if not os.path.exists(file_path):
      await query.edit_message_caption(
          caption=(query.caption or "")
          + f"\n\n❌ រកមិនឃើញ File `{file_path}` លើ Server ទេ។"
      )
      return

    with open(file_path, "rb") as script_file:
      await context.bot.send_document(
          chat_id=buyer_id,
          document=script_file,
          filename=os.path.basename(file_path),
          caption=(
              f"🎉 ការបង់ប្រាក់ត្រូវបានអនុម័ត!\n"
              f"នេះជា File Script សម្រាប់ *{skin['name']}*។"
          ),
          parse_mode="Markdown",
      )
    order["status"] = "APPROVED"
    del ORDERS[order_id]
    await query.edit_message_caption(
        caption=(query.caption or "")
        + "\n\n✅ **APPROVED** — បានផ្ញើ File ទៅអ្នកទិញរួចរាល់។"
    )

  elif action == "reject":
    order["status"] = "REJECTED"
    del ORDERS[order_id]
    await context.bot.send_message(
        chat_id=buyer_id,
        text=(
            f"❌ Order `{order_id}` ត្រូវបានបដិសេធ។ "
            "សូមពិនិត្យការទូទាត់ ឬផ្ញើ Receipt ម្ដងទៀត។"
        ),
        parse_mode="Markdown",
    )
    await query.edit_message_caption(
        caption=(query.caption or "") + "\n\n❌ **REJECTED**"
    )


def main():
  keep_alive()
  app = ApplicationBuilder().token(TOKEN).build()
  app.add_handler(CommandHandler("start", start))
  app.add_handler(CallbackQueryHandler(on_buy, pattern=r"^buy:"))
  app.add_handler(MessageHandler(filters.PHOTO, on_receipt_photo))
  app.add_handler(
      CallbackQueryHandler(on_admin_decision, pattern=r"^(approve|reject):")
  )
  app.run_polling()


if __name__ == "__main__":
  main()
