# Student Assistant Bot V11.9 — Friendly & Popular Student Assistant

**Opt-in coordinated release for all 30 requested feature groups.** This release adds `friendly_v119.py` and a separate Supabase schema; it does not remove or replace Book Library V11.8.8.4, the AI tools, large-file relay, unlimited Smart Bulk, individual PDF forwarding, adult eligibility or group isolation.

## Exact welcome greeting

👋 **السَّلَامُ عَلَيْكُمْ وَرَحْمَةُ اللَّهِ وَبَرَكَاتُهُ**

**Welcome to Student Assistant!** 🎓📚

The greeting appears on the opt-in friendly `/start` screen, and the Arabic greeting also appears in the existing enabled group-join welcome message.

## Before enabling on Render

1. Back up your current project and database. Extract this ZIP **into the existing `StudentAssistantBot` folder**, next to `main.py` and `group_welcome_v11884.py`.
2. In Windows PowerShell run:
   ```powershell
   cd "C:\Users\Pros\Desktop\StudentAssistantBot"
   python -X utf8 INSTALL_FRIENDLY_V119.py --check
   python -X utf8 INSTALL_FRIENDLY_V119.py --apply
   python -X utf8 -m py_compile main.py group_welcome_v11884.py friendly_v119.py
   python -X utf8 -m unittest TEST_FRIENDLY_V119 -q
   python -X utf8 RUN_REGRESSION_SAFE_V1184.py
   ```
   The installer is guarded, backs up changed originals, and is safe to re-run. If `--check` fails, do not force the patch; compare the current production code first.
3. In Supabase, open SQL Editor and execute **`SQL_FRIENDLY_V119.sql`**, reviewing the permissions and backup first. It creates five V11.9-only tables and keeps them inaccessible to public `anon` / `authenticated` roles. The existing Render server-side service-role client uses them.
4. Once the entire regression suite passes, inspect and selectively stage only the intended files:
   ```powershell
   git status --short
   git add -- main.py group_welcome_v11884.py friendly_v119.py SQL_FRIENDLY_V119.sql
   git diff --cached --check
   git diff --cached --stat
   git diff --cached
   git commit -m "Add Friendly Student Experience V11.9"
   git push origin main
   ```
   Optionally include `TEST_FRIENDLY_V119.py` and the feature manifest for reproducibility. **Do not use `git add .`** because the project has unrelated local backups and scripts.
5. Confirm the exact commit deployed successfully to your existing Render service. Then add:
   ```env
   FRIENDLY_V119_ENABLED=true
   FRIENDLY_V119_STATS_ENABLED=true
   ```
   The first flag defaults to **false**. Keep all prior V11.8.8.4 settings and adult-access restrictions unchanged.
6. For inline search in **any Telegram chat**, open @BotFather, run `/setinline`, choose `@Student_Sl_Assistant_bot`, and configure its placeholder. Inline queries are available only to eligible users and return public, approved book deep links.

## The 30 integrated feature groups

See `V119_FEATURE_MANIFEST.json` for the exact list. They cover:

- **12 Friendly UX**: language selector, home menu, typo-tolerant book search, detailed cards, favorites, recent books, categories, existing missing-book requests, bad-metadata reports, searchable-by-category command guide, friendly errors and group-help links.
- **8 Identity / profile**: `/myid`, `/myinfo`, `/chatid`, `/groupinfo`, `/userinfo` (group administrator replying to a message), `/botinfo`, `/mystats`, `/privacy`.
- **10 Engagement / popularity**: `/popular`, `/trending`, share links, ratings + moderated reviews, `/invite`, private admin stats, `/dailybook`, opt-in new-arrivals announcements, inline book discovery and `/feedback`.

Where an earlier feature exists (favorites, book requests, popularity counters, adult verification and language preference), V11.9 **reuses or displays it** instead of removing it. V11.9 save buttons also provide an additional unified personal bookshelf.

## Common commands

| Task | Command |
| --- | --- |
| Friendly home + Arabic/English welcome | `/start` or `/home` |
| Select Tamil, English, Sinhala or Arabic | `/friendlanguage` |
| Search with typo assistance | `/smartbook Sahih al Bukhari` |
| Browse popular/trending | `/popular` or `/trending` |
| Browse categories | `/bookcategories` |
| Saved/recent books | `/mybooks`, `/recentbooks` |
| Daily recommendation | `/dailybook` |
| My Telegram ID/profile/stats | `/myid`, `/myinfo`, `/mystats` |
| Group quick help | `/grouphelp` in an approved library group |
| Group and chat IDs | `/groupinfo`, `/chatid` |
| Information on replied-to user | `/userinfo` for group admins in approved groups |
| Invite friends | `/invite` |
| Book reviews and star ratings | `/ratebook m UUID 5` or use a book card |
| Request missing book | Existing `/bookrequest TITLE` |
| Report incorrect metadata | Use the Report button in a book card or `/reportdetails m UUID ISSUE` |
| New-arrivals announcements opt in/out | `/newarrivals on` or `/newarrivals off` |
| Send feedback | `/feedback Your suggestion...` |
| Explore command guide | `/commands` |
| V11.9 privacy and erase opt-in records | `/privacy`, `/forgetfriendly CONFIRM` |

Admin-only: `/friendadmin`, `/feedbackqueue`, `/reviewqueue`, `/feedbackresolve UUID`, `/reviewapprove UUID`, `/reviewreject UUID`, `/notifynew`.

**Book kinds:** `m` = unified media catalog, `b` = legacy Book Library, followed by the book UUID. Book cards show the relevant buttons without requiring users to type UUIDs.

## Behaviour and important limitations

- **One coordinated release, but not an untested public rollout.** This package passes offline unit/installer checks in a project copy; the user's Windows Python 3.14 full regression, Supabase migration and Render/Telegram live tests are still required.
- **No paid APIs** are needed for the core V11.9 features. Fuzzy suggestions use the existing public catalog and Python standard library; results depend on indexed records and do not guarantee correct spelling for every language.
- **No unapproved books.** Search, inline search, recommendations and popularity only use accessible library records; the existing private delivery and adult-access checks remain in force.
- **No private phone-number lookup.** `/myinfo` only shows fields Telegram supplied; `/userinfo` works for authorized group admins replying to a visible message and only shows public Telegram fields.
- **Opt-in new-arrivals notices** are **admin-triggered** with `/notifynew`, processed in small batches. There is no autonomous recurring background push or cron in this release. Telegram may still rate-limit broadcasts. `/dailybook` is on demand, not an unsolicited daily notification.
- Existing per-user favorites are included where available; V11.9 event-based **recently viewed** begins accumulating only after interactions through its new book-card interface. Existing older activity isn't retroactively reconstructed.
- Ratings with written reviews are **pending** until admin approval; star-only ratings do not need text moderation. Feedback and wrong-book reports are admin-only queues.
- Referral links count voluntary starts and do not award incentives or support unsolicited messaging.
- Admin engagement stats sample at most 3,000 recent V11.9 events; they are not Telegram's actual worldwide user statistics. Public statistics of other users are not exposed.
- `FRIENDLY_V119_STATS_ENABLED=true` enables limited V11.9 event data. Periodically purge old events; the SQL migration comments recommend 90-day retention. `/forgetfriendly CONFIRM` deletes V11.9 data, **not historical messages or records in separate legacy tables**.
- Same Render restart caveat still applies to existing **unlimited Smart Bulk RAM sessions**. V11.9 does not change them.

## Suggested live tests

1. `/start`: check the Arabic greeting and buttons, confirm existing reply-keyboard tools still work.
2. `/friendlanguage`: change Tamil, Sinhala, Arabic and English and verify home-menu translations.
3. `/smartbook Quran`: open a card, tap Save, Rate, Share and Report. Check adult verification and private delivery.
4. `/myid`, `/myinfo`, `/mystats`, `/privacy`, `/invite`, `/dailybook`.
5. Join an approved library group: welcome greeting; `/grouphelp`, `/chatid`, `/groupinfo` and group-admin-only `/userinfo`.
6. `/newarrivals on`: run `/notifynew` as admin to notify subscribers; disable it with `/newarrivals off`.
7. Confirm unauthorized groups and unverified users remain blocked as they were before.
8. Check `/mediabulk`, `/mediabulkdone`, `/mediaforward`, `/book`, and existing PDF tools to avoid regressions.

If any test fails, leave `FRIENDLY_V119_ENABLED=false` on Render, preserving the V11.8.8.4 baseline.
