import os
import logging
import imaplib
import email
from email.header import decode_header
from datetime import datetime
import requests


def decode_part(value):
    if not value:
        return ''
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8', errors='ignore')
        except Exception:
            return value.decode(errors='ignore')
    dh = decode_header(value)
    parts = []
    for text, enc in dh:
        if isinstance(text, bytes):
            try:
                parts.append(text.decode(enc or 'utf-8', errors='ignore'))
            except Exception:
                parts.append(text.decode(errors='ignore'))
        else:
            parts.append(text)
    return ''.join(parts)


logger = logging.getLogger('email_inbound')


def poll_once(sheets_manager, auto_reply=False, ai_reply_func=None, email_client=None):
    host = os.getenv('IMAP_HOST')
    user = os.getenv('IMAP_USER')
    password = os.getenv('IMAP_PASS')
    folder = os.getenv('IMAP_FOLDER', 'INBOX')
    if not host or not user or not password:
        logger.warning("IMAP not configured; skipping poll")
        return {"error": "IMAP not configured"}

    M = imaplib.IMAP4_SSL(host)
    try:
        logger.info(f"IMAP connect to {host}, selecting folder {folder}")
        M.login(user, password)
        M.select(folder)
        # Prefer server-side filtering to reduce load; fall back to broad search
        try:
            typ, data = M.search(None, '(UNSEEN SUBJECT "[Lead:")')
            if typ != 'OK':
                typ, data = M.search(None, '(UNSEEN)')
        except Exception:
            typ, data = M.search(None, '(UNSEEN)')
        if typ != 'OK':
            logger.info("IMAP search OK!=OK; processed 0")
            return {"status": "ok", "processed": 0}
        ids = data[0].split()
        logger.info(f"IMAP unread count: {len(ids)}")
        processed = 0
        for i in ids:
            try:
                typ, msg_data = M.fetch(i, '(RFC822)')
                if typ != 'OK':
                    logger.warning(f"IMAP fetch failed for id {i}")
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                subject = decode_part(msg.get('Subject'))
                from_addr = decode_part(msg.get('From'))
                x_lead_uuid = msg.get('X-Lead-UUID') or ''
                in_reply_to = decode_part(msg.get('In-Reply-To') or '')
                references = decode_part(msg.get('References') or '')
                message_id = decode_part(msg.get('Message-ID') or '')
                logger.info(f"Processing message: from={from_addr}, subject={subject}, x_lead_uuid={x_lead_uuid}")
                # Fast filter: only handle replies to our emails (reply headers) and carrying our tag/header
                if (not in_reply_to and not references):
                    logger.info("Skipping message without reply threading headers")
                    continue
                if ('[Lead:' not in subject) and (not x_lead_uuid.strip()):
                    logger.info("Skipping message without lead tag/header")
                    continue
                # Get body text
                body_text = ''
                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        disp = str(part.get('Content-Disposition') or '')
                        if ctype == 'text/plain' and 'attachment' not in disp:
                            body_text = decode_part(part.get_payload(decode=True))
                            break
                else:
                    body_text = decode_part(msg.get_payload(decode=True))

                # Resolve lead row by uuid or by email From fallback
                lead_uuid = x_lead_uuid.strip()
                row_index_0 = None
                if lead_uuid:
                    row_index_0 = sheets_manager.find_row_by_lead_uuid(lead_uuid)
                    logger.info(f"Row by header X-Lead-UUID: {row_index_0}")
                if row_index_0 is None:
                    try:
                        ws = sheets_manager.sheet.worksheet('Leads')
                        records = ws.get_all_records()
                        for idx, rec in enumerate(records):
                            if rec.get('email') and rec['email'] in from_addr:
                                row_index_0 = idx
                                lead_uuid = rec.get('lead_uuid', '')
                                break
                    except Exception:
                        pass
                if row_index_0 is None and '[Lead:' in subject:
                    try:
                        tag = subject.split('[Lead:')[-1]
                        tag_uuid = tag.split(']')[0].strip()
                        if tag_uuid:
                            row_index_0 = sheets_manager.find_row_by_lead_uuid(tag_uuid)
                            if row_index_0 is not None:
                                lead_uuid = tag_uuid
                        logger.info(f"Row by subject tag: {row_index_0}, lead_uuid={lead_uuid}")
                    except Exception:
                        pass
                if row_index_0 is None:
                    logger.warning("Unable to map inbound email to lead; skipping")
                    continue

                # Log inbound
                logger.info(f"Logging inbound for lead_uuid={lead_uuid} row={row_index_0}")
                sheets_manager.log_conversation(
                    lead_uuid=lead_uuid or '',
                    channel='email',
                    direction='in',
                    timestamp=datetime.now().isoformat(),
                    subject=subject,
                    content=body_text,
                    summary='',
                    metadata='',
                    message_id=message_id,
                    status='received'
                )

                # Optional auto-reply via AI
                if auto_reply and email_client is not None:
                    try:
                        logger.info("Auto-reply enabled; generating AI reply")
                        if callable(ai_reply_func):
                            reply_text = ai_reply_func(lead_uuid, subject, body_text)
                        else:
                            reply_text = _generate_ai_reply(sheets_manager, lead_uuid, subject, body_text)
                        logger.info(f"AI reply length: {len(reply_text or '')}")
                        if not reply_text:
                            # Fallback minimal reply if model returns empty
                            reply_text = (
                                "Thanks for your message! Happy to help with accommodation. "
                                "Could you share your destination country (USA, Canada, UK, Ireland, France, Spain, Germany, Australia) "
                                "and your intake month/year? – Eshwari, Amber Student"
                            )
                        # Get recipient from sheet
                        ws = sheets_manager.sheet.worksheet('Leads')
                        rec = ws.get_all_records()[row_index_0]
                        to_email = rec.get('email') or ''
                        # Fallback to From address if sheet email missing
                        try:
                            from_email_only = (from_addr.split('<')[-1].split('>')[0] if '<' in from_addr else from_addr).strip()
                        except Exception:
                            from_email_only = ''
                        if not to_email and from_email_only and '@' in from_email_only:
                            logger.info("Sheet email missing; using From address as recipient")
                            to_email = from_email_only
                        logger.info(f"Reply destination resolved to: {to_email or 'EMPTY'}")
                        if to_email and reply_text:
                            headers = {'X-Lead-UUID': lead_uuid}
                            if message_id:
                                headers['In-Reply-To'] = message_id
                                headers['References'] = message_id
                            logger.info(f"Sending AI email reply to {to_email}")
                            try:
                                email_client.send(
                                    to_email=to_email,
                                    subject=f"Re: {subject}",
                                    body_text=reply_text,
                                    extra_headers=headers
                                )
                                sent_ok = True
                                logger.info("AI reply sent successfully")
                            except Exception as send_err:
                                sent_ok = False
                                logger.error(f"SMTP send failed: {send_err}", exc_info=True)
                            logger.info("Logged outbound AI reply to Conversations")
                            sheets_manager.log_conversation(
                                lead_uuid=lead_uuid or '',
                                channel='email',
                                direction='out',
                                timestamp=datetime.now().isoformat(),
                                subject=f"Re: {subject}",
                                content=reply_text,
                                summary='',
                                metadata=('status=sent' if sent_ok else 'status=send_failed'),
                                message_id='',
                                status=('sent' if sent_ok else 'failed')
                            )
                    except Exception as e:
                        logger.error(f"AI auto-reply failed: {e}", exc_info=True)

                processed += 1
                # mark as seen
                M.store(i, '+FLAGS', '\\Seen')
            except Exception as e:
                logger.error(f"Error processing inbound message {i}: {e}", exc_info=True)
        logger.info(f"Poll complete. processed={processed}")
        return {"status": "ok", "processed": processed}
    finally:
        try:
            M.close()
        except Exception:
            pass
        try:
            M.logout()
        except Exception:
            pass

def _generate_ai_reply(sheets_manager, lead_uuid: str, subject: str, inbound_text: str) -> str:
    """Generate an email reply using OpenAI with conversation context."""
    api_key = os.getenv('OPENAI_API_KEY')
    model = os.getenv('OPENAI_MODEL') or os.getenv('AI_MODEL', 'gpt-4.1-mini')
    if not api_key:
        return ''

    # Fetch recent context
    try:
        history = sheets_manager.get_conversations_by_lead(lead_uuid) or []
        # sort by time and take last 8
        history_sorted = sorted(history, key=lambda x: x.get('timestamp', ''))[-8:]
        history_snippets = []
        for h in history_sorted:
            role = 'assistant' if h.get('direction') == 'out' else 'user'
            ch = h.get('channel') or 'email'
            content = (h.get('subject') or '') + "\n" + (h.get('content') or '')
            history_snippets.append({'role': role, 'content': f"[{ch}] {content}"})
    except Exception:
        history_snippets = []

    system_prompt = (
        "You are Eshwari, a warm, natural-sounding student advisor at Amber.\n"
        "Persona: approachable, empathetic, conversational; acknowledge answers; gentle guidance.\n"
        "Environment: first touch with student leads from trusted partners; build trust; verify study intent; understand housing needs; pass qualified leads to support.\n"
        "Tone: natural, friendly, concise; no overselling.\n"
        "Supported countries: USA, Canada, UK, Ireland, France, Spain, Germany, Australia.\n"
        "Goal: send ONE concise email asking for all missing key details at once, without back-and-forth.\n"
        "Ask (if not already provided): destination country/city/university, rough budget, intake timeline (month/year), visa status, housing need & preference (student housing / private / shared), and preferred contact channel (WhatsApp/Call/Email).\n"
        "If details are already present, confirm them briefly and request only the missing ones. Keep 4-8 short lines.\n"
        "If unsupported country or no study intent, politely end. Sign off as Eshwari, Amber Student."
    )

    user_prompt = (
        f"Inbound subject: {subject}\n\n"
        f"Inbound message:\n{inbound_text.strip()}\n\n"
        "Write a concise email reply body only (no quoted thread).\n"
        "Request all missing key details at once, formatted clearly (short lines or bullets).\n"
        "Be friendly and helpful; avoid long paragraphs."
    )

    messages = [{"role": "system", "content": system_prompt}] + history_snippets + [{"role": "user", "content": user_prompt}]

    try:
        resp = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': model,
                'messages': messages,
                'temperature': float(os.getenv('AI_TEMPERATURE', '0.4')),
                'max_tokens': int(os.getenv('AI_MAX_TOKENS', '300'))
            }, timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        return (content or '').strip()
    except Exception as e:
        logger.error(f"OpenAI completion failed: {e}", exc_info=True)
        return ''


