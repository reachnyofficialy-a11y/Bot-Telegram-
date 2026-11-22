import json
import os
import uuid
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
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


def get_main_reply_keyboard():
  return ReplyKeyboardMarkup(
      [
          [KeyboardButton("🛒 ទិញ Skin ($1)"), KeyboardButton("📜 បញ្ជី Skin")],
          [KeyboardButton("ℹ️ របៀបទិញ")],
          [
              KeyboardButton("📩 ទាក់ទង Admin"),
              KeyboardButton("📦 Order របស់ខ្ញុំ"),
          ],
      ],
      resize_keyboard=True,
  )


async def send_skin_catalog(message_target):
  keyboard = [
      [
          InlineKeyboardButton(
              f"{item['name']} - ${item['price_usd']:.0f}",
              callback_data=f"buy:{skin_id}",
          )
      ]
      for skin_id, item in CATALOG.items()
  ]

  keyboard.append([
      InlineKeyboardButton("ℹ️ របៀបទិញ", callback_data="how_to_buy"),
      InlineKeyboardButton("📩 Admin", url=f"tg://user?id={ADMIN_ID}"),
  ])

  await message_target.reply_text(
      "សូមជ្រើសរើស Skin Script ($1 / skin):",
      reply_markup=InlineKeyboardMarkup(keyboard),
  )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(
      "សូមស្វាគមន៍មកកាន់ហាងលក់ Skin Script ($1 / skin)!",
      reply_markup=get_main_reply_keyboard(),
  )
  await send_skin_catalog(update.message)


async def on_reply_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
  text = (update.message.text or "").strip()

  if text in ("🛒 ទិញ Skin ($1)", "📜 បញ្ជី Skin"):
    await send_skin_catalog(update.message)
  elif text == "ℹ️ របៀបទិញ":
    await update.message.reply_text(
        "1. ជ្រើសរើស Skin Script ($1)\n"
        "2. ស្កេន KHQR រួចផ្ញើរូបភាព Receipt ចូល Bot\n"
        "3. រង់ចាំ Admin Approve ដើម្បីទទួលបាន File Script"
    )
  elif text == "📩 ទាក់ទង Admin":
    await update.message.reply_text(
        f"សូមទាក់ទង Admin តាមរយៈ៖ tg://user?id={ADMIN_ID}"
    )
  elif text == "📦 Order របស់ខ្ញុំ":
    user_id = update.effective_user.id
    user_orders = [o for o in ORDERS.values() if o["user_id"] == user_id]
    if not user_orders:
      await update.message.reply_text("អ្នកមិនទាន់មាន Order ណាមួយនៅឡើយទេ។")
      return
    lines = ["📦 **Order របស់អ្នក：**"]
    for o in user_orders[-5:]:
      lines.append(f"• `{o['order_id']}` — {o['skin_name']} ({o['status']})")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def on_how_to_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.callback_query
  await query.answer()
  await query.message.reply_text(
      "1. ជ្រើសរើស Skin Script ($1)\n"
      "2. ស្កេន KHQR រួចផ្ញើរូបភាព Receipt ចូល Bot\n"
      "3. រង់ចាំ Admin Approve ដើម្បីទទួលបាន File Script"
  )


async def add_skin(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user = update.effective_user
  if not user or user.id != ADMIN_ID:
    await update.message.reply_text("ពាក្យបញ្ជានេះសម្រាប់តែ Admin ប៉ុណ្ណោះ។")
    return

  raw_text = update.message.text.replace("/addskin", "", 1).strip()
  parts = [p.strip() for p in raw_text.split("|") if p.strip()]

  if len(parts) < 2:
    await update.message.reply_text(
        "ទម្រង់ប្រើប្រាស់៖\n"
        "`/addskin | skin_id | ឈ្មោះ Skin | scripts/file.lua`\n\n"
        "ឧទាហរណ៍：\n"
        "`/addskin | nolan_skin | Nolan Skin Script | scripts/nolan_skin.lua`",
        parse_mode="Markdown",
    )
    return

  skin_id = parts[0].lower().replace(" ", "_")
  skin_name = parts[1]
  file_path = parts[2] if len(parts) >= 3 else f"scripts/{skin_id}.lua"

  CATALOG[skin_id] = {
      "name": skin_name,
      "price_usd": 1,
      "file_path": file_path,
  }

  try:
    with open("catalog.json", "w", encoding="utf-8") as f:
      json.dump(CATALOG, f, ensure_ascii=False, indent=2)
  except Exception:
    pass

  await update.message.reply_text(
      f"✅ បាន Add Skin ថ្មីរួចរាល់!\n"
      f"• ID: `{skin_id}`\n"
      f"• ឈ្មោះ: *{skin_name}*\n"
      f"• តម្លៃ: *$1*\n"
      f"• File Path: `{file_path}`\n\n"
      "វាយ `/start` ដើម្បីមើលប៊ូតុង Skin ថ្មីក្នុង Menu។",
      parse_mode="Markdown",
  )


async def upload_skin(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user = update.effective_user
  if not user or user.id != ADMIN_ID:
    await update.message.reply_text("ពាក្យបញ្ជានេះសម្រាប់តែ Admin ប៉ុណ្ណោះ។")
    return

  doc = update.message.document
  if not doc:
    await update.message.reply_text(
        "សូមផ្ញើ **File Script** (Document) ដោយដាក់ Caption តាមទម្រង់៖\n"
        "`/uploadskin | skin_id | ឈ្មោះ Skin`\n\n"
        "ឧទាហរណ៍：\n"
        "`/uploadskin | nolan_skin | Nolan Skin Script`",
        parse_mode="Markdown",
    )
    return

  caption = (update.message.caption or "").replace("/uploadskin", "", 1).strip()
  parts = [p.strip() for p in caption.split("|") if p.strip()]

  if len(parts) < 2:
    await update.message.reply_text(
        "ខ្វះព័ត៌មានក្នុង Caption! សូមដាក់តាមទម្រង់：\n"
        "`/uploadskin | nolan_skin | Nolan Skin Script`",
        parse_mode="Markdown",
    )
    return

  skin_id = parts[0].lower().replace(" ", "_")
  skin_name = parts[1]

  os.makedirs("scripts", exist_ok=True)
  safe_filename = os.path.basename(doc.file_name or f"{skin_id}.lua")
  file_path = os.path.join("scripts", safe_filename)

  tg_file = await context.bot.get_file(doc.file_id)
  await tg_file.download_to_drive(custom_path=file_path)

  CATALOG[skin_id] = {
      "name": skin_name,
      "price_usd": 1,
      "file_path": file_path,
  }

  try:
    with open("catalog.json", "w", encoding="utf-8") as f:
      json.dump(CATALOG, f, ensure_ascii=False, indent=2)
  except Exception:
    pass

  await update.message.reply_text(
      f"✅ បាន Upload File និង Add Skin ថ្មីរួចរាល់!\n"
      f"• ID: `{skin_id}`\n"
      f"• ឈ្មោះ: *{skin_name}*\n"
      f"• តម្លៃ: *$1*\n"
      f"• File: `{file_path}`\n\n"
      "វាយ `/start` ដើម្បីមើលប៊ូតុង Skin ថ្មីក្នុង Menu។",
      parse_mode="Markdown",
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
    order["status"] = "APPROVED"
    PENDING_RECEIPT_USER.pop(order["user_id"], None)

    if os.path.exists(file_path):
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
    else:
      await context.bot.send_message(
          chat_id=order["user_id"],
          text=(
              f"🎉 ការទូទាត់សម្រាប់ Order `{order_id}` ត្រូវបាន Approve!\n"
              f"Skin: **{order['skin_name']}** (តម្លៃ ${order['price_usd']:.0f})\n"
              "ℹ️ File Script កំពុងរៀបចំ/ផ្ញើជូនតាមក្រោយ។"
          ),
          parse_mode="Markdown",
      )

    await query.edit_message_caption(
        caption=(query.message.caption or "") + "\n\n✅ APPROVED"
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
  app.add_handler(CommandHandler("addskin", add_skin))
  app.add_handler(CallbackQueryHandler(on_how_to_buy, pattern=r"^how_to_buy$"))
  app.add_handler(CallbackQueryHandler(on_buy, pattern=r"^buy:"))
  app.add_handler(MessageHandler(filters.Document.ALL, upload_skin))
  app.add_handler(MessageHandler(filters.PHOTO, on_photo))
  app.add_handler(
      CallbackQueryHandler(on_admin_decision, pattern=r"^(approve|reject):")
  )
  app.add_handler(
      MessageHandler(
          filters.TEXT & ~filters.COMMAND,
          on_reply_menu,
      )
  )

  app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
  main()
