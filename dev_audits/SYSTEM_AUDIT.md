# ChuoSmart (chuo-market3) — Full System Audit & Documentation

> Purpose: This document is a complete technical description of the **ChuoSmart** platform
> (project directory: `chuo-market3`). It is intended to be handed to an AI (e.g. ChatGPT)
> so that it can understand the system and generate accurate prompts / plans / code changes.
>
> Generated: 2026-08-15

---

## 1. Executive Overview

**ChuoSmart** is a Tanzanian ed-tech / marketplace platform for university students. It combines:

- **E-commerce marketplace** (students buy/sell products — phones, books, electronics, etc.)
- **LMS (Learning Management System)** — courses, modules, quizzes (incl. AI-generated "mastery checks"), grades, certificates
- **Job portal** — with external job-fetching integrations (Ajira, LinkedIn, Indeed, Adzuna, BrighterMonday)
- **Affiliate program** — referral tracking and commission payouts
- **Materials library** — users share software/tools/resources with links
- **Newsletter + web push notifications + SEO** infrastructure

Domain: `chuosmart.com`

---

## 2. Technology Stack

| Concern | Technology |
|---|---|
| Backend | Django **4.2.20** (Python 3.12 via `.venv`) |
| API | Django REST Framework 3.16.1 (minimal usage) |
| Frontend | Server-rendered Django templates + Bootstrap 5, TinyMCE 5 rich text, vanilla JS |
| Database | Production: **MySQL** (`utf8mb4` charset, emoji support). Dev fallback comments reference SQLite (`db.sqlite3`). PyMySQL used as MySQLdb driver. |
| Task scheduling | Removed APScheduler. Uses **management commands** + uptime-robot-triggered maintenance endpoint (`/jobs/update-jobs/`) + DB-backed `QuizGenerationJob` queue |
| AI / LLM | **Cerebras Cloud SDK** (`cerebras-cloud-sdk`), model `zai-glm-4.7` — AI quiz generation, job→course recommendations |
| Payments | **Snippe** payment gateway (`snippe==0.1.4`): mobile-money / card hosted checkout, webhooks |
| Media storage | **Cloudinary** (`django-cloudinary-storage`) for images; local `media/` also supported |
| Push notifications | `django-webpush` (VAPID keys in env) |
| Email | SMTP (`server311.web-hosting.com:465`, SSL) as `support@chuosmart.com` |
| Static serving | WhiteNoise (`CompressedStaticFilesStorage`) |
| PDF | `pdfkit` (in requirements, used for certificate generation) |
| WSGI server | Gunicorn |

### Key Python packages
`Django`, `djangorestframework`, `cloudinary`, `django-cloudinary-storage`, `django-tinymce`, `django-crispy-forms`, `django-widget-tweaks`, `django-webpush`, `django-model-utils`, `cerebras-cloud-sdk`, `snippe`, `PyMySQL`, `python-dotenv`, `dj-database-url`, `whitenoise`, `gunicorn`, `pdfkit`, `pandas`, `bleach`, `requests`, `Pillow` (commented out but needed for image ops), `qrcode` (used in certificates).

---

## 3. Project Structure

```
chuo-market3/
├── Commerce/                 # Project configuration package
│   ├── settings.py           # All Django settings
│   ├── urls.py               # Root URLconf
│   ├── wsgi.py / asgi.py
│   └── test_settings.py      # Test-specific DB/config
├── core/                     # Marketplace, users, blogs, newsletter, SEO, middleware
├── lms/                      # Learning Management System (largest app)
│   ├── models/               # models package (models.py is the real one)
│   ├── certificates.py       # Certificate rendering/signing helpers
│   ├── ai_assessments.py     # Cerebras AI quiz generation
│   └── ...
├── jobs/                     # Job portal + external API integrations
├── affiliates/               # Affiliate program
├── materials/                # Educational resources / software links library
├── landing/                  # Landing page + email signup
├── templates/                # Global templates (base.html, emails, error pages)
├── static/                   # Global static assets
├── media/                    # Local media (dev / fallback)
├── logs/                     # email.log, lms.log
├── dev_audits/               # This audit
└── manage.py
```

---

## 4. Django Applications Detail

### 4.1 `core` — Marketplace & Site-Wide
Handles products, cart, orders, blogs, subscriptions, customers, newsletter, SEO, security middleware.

**Models** (in `core/models.py`):
- `Subscription` — Free/Bronze/Silver/Gold tiers, prices in TZS, benefits text
- `Customer` — OneToOne with `User`; university/college choices sourced from `universities_colleges_tanzania.py`; block/room number, phone
- `Product` — user, title, slug (auto), category (Mobiles/Electronics/Books/Clothing/Accessories/Services), description, price, discount_price, image + auto-generated `image_webp` (via `core/image_utils.py` optimize_image)
- `Cart` — user, product, quantity
- `OrderPlaced` — user, customer, product, quantity, ordered_date, price, status (Delivered/Pending/Cancelled/On The Way/Received/Paid)
- `Banners` — home page banners
- `Blog` — title, slug, content (TinyMCE HTML or Markdown), author, thumbnail (local + `thumbnail_cloudinary` URL + `thumbnail_webp`), `upload_method`, `is_markdown`, category; extensive `clean_html_content()` regex sanitizer in `save()`
- `SubscriptionPayment` — payment_proof image, status Pending/Verified/Rejected (manual verification model)
- `NewsletterSubscriber` — email (unique), source, is_active
- `UserNewsletterPreference` — per-user newsletter opt-in; patched onto `User.newsletter` property via `User.add_to_class`
- `SentEmail` — audit log of admin-sent emails
- `NewsletterSendLog` — dedupe daily digest per subscriber (unique email+date)
- `NewsletterTestSend` — admin test sends log
- `AccountDeletionRequest` — compliance (GDPR-style) deletion requests for `chuosmart` and `potea_pata` products

**Key views** (`core/views.py`, ~1838 lines): home, marketplace, product_detail (slug or pk), cart add/remove/plus/minus, checkout, order_placed, profile, address, orders, login/logout/registration/change_password, search, add/edit/delete product & blog, blog list/detail, subscription view + payment proof upload, `upload_tinymce_image` (Cloudinary), `account_deletion_request`, `newsletter_settings`, `newsletter_confirm_unsubscribe` (token), `robots_txt`, `csrf_failure`, debug/emergency blog views.

**Support modules:**
- `core/image_utils.py` — `optimize_image()` converts to WebP, quality/size control
- `core/canonicalization.py` — `CanonicalDomainMiddleware`, `TrailingSlashMiddleware` (URL canonicalization to `chuosmart.com`)
- `core/middleware.py` — `SecurityHeadersMiddleware` (CSP, Referrer-Policy, Permissions-Policy, COOP), `SessionIdleTimeoutMiddleware`
- `core/sitemaps.py` — Product, Blog, Job, Static sitemaps
- `core/seo_context.py` / `core/context_processors.py` — SEO context, auth status, dashboard notification, site ad toggles, certificate banners
- `core/newsletter.py` — newsletter digest builder/sender (daily), categories
- `core/notifications.py` — webpush send helpers
- `core/help_center.py` / `core/help_views.py` — help center
- `core/templatetags/` — `optimized_img`, HTML sanitize filters, class injection
- `core/universities_colleges_tanzania.py` — static dataset of Tanzanian universities & colleges
- `core/forms.py`, `core/signals.py`, `core/admin.py`, `core/decorators/`

### 4.2 `lms` — Learning Management System (LARGEST app)
SkyLearn-inspired academic LMS with paid-course gating and certificates.

**Models** (`lms/models/models.py`, ~1626 lines; note `lms/models.py` is a legacy/duplicate file):
- `ActivityLog` — audit log for course/program changes
- `Semester` — year + semester, `is_current_semester` flag
- `LMSProfile` — OneToOne User; role (student/instructor/admin), bio, picture, phone, `legal_name` (required for certificates)
- `Program` — academic program
- `Course` — course_type (university/general), title, slug, summary, content, `is_free`, image (auto WebP-optimized), instructors (M2M LMSProfile), students (M2M through CourseEnrollment); university-only fields: code (unique), credit, program FK, level, year, semester, is_elective; also `is_pinned`, `price` (Decimal, TZS), created_at. Methods: `user_has_access()`, `user_has_any_access()`, `get_direct_url()` (bypasses ad interstitial)
- `PaymentMethod` — instructor bank/lipa number, instructions, image
- `CourseEnrollment` — student, course; `payment_status` (not_required/pending/approved/rejected), payment_proof, payment_date, payment_method, payment_approved_by/date, notes; `admin_granted_access`, `admin_granted_certificate`, `certificate_prepaid`, `granted_by`; `has_access` property; auto-status logic in `save()`
- `CourseModule` — title, description, course FK, order, `price` (TZS; enables single-module paid access), `skip_assessment` (overview modules). Rich access-control API: `previous_module_accessible_for_request`, `is_request_eligible_for`, `get_next_module`, `get_progress_for`, `has_admin_module_access`, `is_paid_for`, `is_unlocked_for`, `is_locked_for`, `lock_message_for` (sequential module gating with 70% pass requirement)
- `CourseContent` — title, module FK, content_type (document/video/link/text), document (pdf/doc/ppt/xls/txt validator), video_url, external_link, text_content, order
- `ContentAccess` — student × content, accessed_at, completed, completed_at
- `ModuleAccessGrant` — admin-granted single-module access (student, module, active, notes, granted_by); post_save auto-enrolls student in course
- `ModulePayment` — Snippe payment for single-module access (session id, reference, webhook event id, amount, status, checkout_url, payment_link_url, failure_reason)
- `ModuleAccessRequest` — student module access request; auto-`approve()` after successful Snippe payment creates a `ModuleAccessGrant`
- `Quiz` — course FK, title, slug, description, module FK, `generated_for` (LMSProfile, for personalized AI quizzes), category, random_order, answers_at_end, exam_paper, single_attempt, `pass_mark` (default **70**), draft, due_date, `generation_status` (pending/processing/ready/failed), `ai_generated`, generation timestamps. DB constraints enforce one personal AI quiz per (module,student) and one shared AI quiz per module.
- `Question` (abstract base) → `MCQuestion`, `TF_Question`, `Essay_Question`; `Choice` for MC
- `QuizTaker` — user, quiz, score, completed, dates; `passed` property
- `StudentAnswer` — answers per question (mc/tf/essay text/file)
- `ModuleProgress` — student × module gate status: `content_completed`, `assessment_passed`, `best_score`, `best_quiz_taker`, `completed_at`; `PASSING_PERCENTAGE = 70`; `unlocks_next` property
- `Grade` — student × course × semester; attendance/assignment/mid_exam/final_exam, auto `total`, `grade` (A–F), comment
- `InstructorRequest` — request to become instructor (reason, qualifications, CV, status, admin_notes)
- `SiteSettings` — single-instance: `show_ads_before_free_courses`
- `CoursePayment` — Snippe payment for paid course enrollment
- `CertificatePayment` — Snippe payment for certificate download (default amount 15000 TZS)
- `StudentCertificate` — student, course, template, `certificate_id` (format `CHUO-YYYYMMDD-XXXXXXXXXX`), issued_at, expires_at, is_valid; verification_status property
- `CertificateTemplate` — rich visual config: style (classic/modern/minimal/academic/corporate), orientation, colors, background/border/font style, logo/signature/seal/watermark images, template body with `{{ placeholders }}`, price, completion_percentage, verification toggle, QR toggle, expiry, status (draft/active/archived)
- `QuizGenerationJob` — DB-backed AI quiz queue (status, force, question_count, attempts, max_attempts, error, locked_at)

**Key views** (`lms/views.py`, ~3525 lines): LMS home, student/instructor dashboards, program/course CRUD (class-based with permission mixins), enroll/unenroll, module & content CRUD, quiz flow (detail, start, question-by-question, complete, results), question adders, grades, certificate template CRUD, `verify_certificate`, `certificate_detail`, `download_certificate` (requires payment unless `admin_granted_certificate`/`certificate_prepaid`), `certificate_payment_init`, `snippe_webhook` (CSRF-exempt, idempotent webhook for all payment types), `grade_students`, payment flows: `payment_form` (manual proof upload), `course_payment_init` (Snippe pay-first), `module_access_payment` / `module_payment_init` / `module_payment_success`, instructor payment-method CRUD, `request_instructor_role`, `set_legal_name` (+`legal_name_required` decorator), `session_keep_alive`, `toggle_ad_exemption`.

**AI assessments** (`lms/ai_assessments.py`, ~768 lines): generates personalized mastery-check quizzes per module/student via Cerebras; strict vs fallback modes controlled by `CEREBRAS_STRICT_ASSESSMENTS`; queues via `QuizGenerationJob`; management command `process_quiz_generation_jobs`.

**Certificates** (`lms/certificates.py`): template rendering, HMAC-SHA256 signed verification URLs (`?sig=`), QR code data URIs, name resolution (legal name > full name > username).

**Other:** `lms/forms.py`, `lms/signals.py`, `lms/utils.py`, `lms/templatetags/`, `lms/admin.py`.

### 4.3 `jobs` — Job Portal
**Models** (`jobs/models.py`):
- `Company` — name, description (HTML), website, logo, address/city/country, contact, created_by, is_verified
- `Industry`, `Skill` — taxonomy
- `Job` — title, description (HTML), company, industry, location, is_remote, salary_min/max + currency, job_type, experience_level, requirements/responsibilities/benefits (HTML), deadline, posted_date, is_active, is_featured, views_count, applications_count, created_by, skills M2M, `job_posting_type` (internal/external), source/external_id/external_url (API ingestion). Indexed fields. `public_queryset()` visibility rules (creator approval + company verification for internal postings). DB indexes on title/location/job_type/source/external_id.
- `JobApplication` — job, applicant, cover_letter, resume (file), phone, portfolio_url, additional_documents, availability, salary_expectation, status (pending→hired), employer_notes; unique (job, applicant)
- `SavedJob` — unique (job, user)
- `JobSearchPreference` — per-user notification preferences (job_types, locations, keywords, industries, skills, salary_min, frequency)
- `ApiConfiguration` — credentials for LinkedIn/Indeed/Adzuna/BrighterMonday/Ajira; active flag, daily_limit, request_count, last_fetch
- `ApiRequestLog` — audit of API fetches (status, jobs fetched/created/updated, execution time)
- `UserJobApproval` — approval gate for users posting public jobs
- `JobCourseRecommendation` — cached Cerebras-generated course recommendations per job (source: cerebras/fallback, reasons JSON)

**Integration** (`jobs/api_integration.py`, ~1021 lines): fetches jobs from external APIs — **Ajira** (Tanzania government job portal, custom scraper), LinkedIn, Indeed, Adzuna, BrighterMonday. `fetch_all_jobs()`. Config via `ApiConfiguration` records.
**Recommendations** (`jobs/recommendations.py`): Cerebras-driven job→course recommendations with fallback (keyword matching).
**Scheduler**: APScheduler removed; `jobs/scheduler.py` exposes `fetch_jobs_manually()`. Jobs are triggered via `/jobs/update-jobs/` maintenance endpoint (called by uptime robots) and management commands.
**Management commands:** `fetch_jobs`, `fetch_ajira_jobs`, `delete_ajira_jobs`, `seed_dummy_jobs`, `populate_skills`, `populate_industries`.
**Docs:** `jobs/README.md`, `jobs/AJIRA_SETUP_GUIDE.md`, `jobs/README_AJIRA_SCRAPER.md`.

### 4.4 `affiliates` — Affiliate Program
**Models** (`affiliates/models.py`):
- `Affiliate` — OneToOne User, unique `affiliate_code` (auto `username[:5]-XXXXX`), balance, status (active/pending/rejected/suspended), phone, payment_method, payment_details JSON, total_earnings, total_paid
- `Referral` — affiliate, referred_user, generic FK (content_type/object_id) to Course/Product/Service, referral_type, `referral_id` (UUID), `commission_earned` (auto = purchase_amount × `AFFILIATE_COMMISSION_RATE` default 0.10), is_paid, purchase_amount
- `ClickTracking` — affiliate, referral_link, ip_address, user_agent, timestamp, converted
- `PayoutRequest` — amount, status (pending/approved/rejected/paid), payment_method, details

**Middleware** (`affiliates/middleware.py`): `ReferralMiddleware` captures `/ref/<username>/<product_id>` and `?ref=CODE`, sets session cookie + `ClickTracking` record, redirects to product/course.
**Views**: dashboard, register, settings, stats, referrals, payouts, request_payout, terms, generate_link, referral_link.
**Signal/support**: `affiliates/signals.py`, `affiliates/management/commands/process_payouts.py`.

### 4.5 `materials` — Materials Library
- `Material` — created_by, title, description, category (software/developer_tools/education/productivity/design/ai_tools/other), software_url, created_at, updated_at, is_active
- Views: list, detail, create, update, delete (owner/staff only for edit/delete). Included in global search and newsletter categories.

### 4.6 `landing` — Marketing Landing
- `EmailSignup` — email (unique), date_joined, purpose (default: digital marketing course enrollment)
- Single view `landing_page`.

---

## 5. URL Map (Root `Commerce/urls.py`)

| Prefix | App | Notes |
|---|---|---|
| `/` | core | marketplace, products, cart, checkout, auth, blogs, subscription, profile, dashboard, account-deletion, password reset, notifications, sitemap helpers, `/api/upload-tinymce-image/` |
| `/lms/` | lms | courses, modules, content, quizzes, grades, certificates, payments, webhooks, instructor mgmt |
| `/jobs/` | jobs | listings, apply, companies, applications, preferences, `/jobs/update-jobs/` maintenance |
| `/affiliates/` | affiliates | dashboard, referral links |
| `/materials/` | materials | resources library |
| `/landing/` | landing | landing page |
| `/webpush/` | webpush | browser push subscription |
| `/admin/` | Django admin | |
| `/sitemap.xml` | core.sitemaps | products/blogs/jobs/static |
| `/robots.txt` | core.views.robots_txt | |

### Webhooks
- `/lms/webhooks/snippe/` — Snippe payment webhook, `@csrf_exempt`, handles course, module, and certificate payment confirmation with webhook-event idempotency.

---

## 6. Key Feature Flows

### 6.1 Authentication & Users
- Standard Django auth: register (`customerregistration`), login, logout, change password, password reset (24h timeout).
- Two profile extensions: `core.Customer` (marketplace) and `lms.LMSProfile` (LMS roles).
- `management/commands/sync_lms_profiles.py` keeps LMS profiles in sync.
- Account deletion requests (data-privacy compliance) with admin review workflow.

### 6.2 Marketplace / E-commerce
- Product CRUD by owner, image auto-WebP optimization.
- Cart (add/plus/minus/remove), checkout, `OrderPlaced` status tracking.
- Buy-now flow, category browse, search, product slug URLs with pk fallback for old links.
- **No online payment for marketplace orders** — cash/manual ("order placed" only).

### 6.3 LMS Access Control (paid courses)
1. Free courses → anyone enrolled directly.
2. Paid courses → two models:
   - **Manual proof**: `payment_form` → student uploads payment proof → admin approves (`payment_status=approved`) → access granted.
   - **Pay-first via Snippe**: `course_payment_init` → hosted checkout → webhook completes `CoursePayment` → auto-enroll + approve.
3. **Single-module purchase**: modules with a `price` can be bought individually via `ModulePayment` → auto `ModuleAccessRequest.approve()` → `ModuleAccessGrant` → auto-enrollment. Sequential gating: module N requires module N-1 completed + quiz passed (70%).
4. `skip_assessment` modules are free/overview (no quiz gate).
5. Instructors/admins always bypass gates. Admin can grant access without payment (`admin_granted_access`, `admin_granted_certificate`, `certificate_prepaid`).

### 6.4 Quizzes & AI Mastery Checks
- Manual question types: MC (with choices), True/False, Essay (text/file/both).
- AI-generated personalized quizzes per (module, student) via Cerebras (`ai_assessments.py`), queued via `QuizGenerationJob`, processed by `process_quiz_generation_jobs` command. Strict mode prevents fallback to static questions.
- Quiz flow: start → one question per page → complete → results; single-attempt / exam-paper options; pass mark configurable (default 70).
- Module gating uses best quiz score.

### 6.5 Certificates
- Only after all modules completed (content + assessments).
- Requires `legal_name` (blocking flow via `set_legal_name`).
- Downloadable only if: payment completed, `admin_granted_certificate`, or `certificate_prepaid`; global toggle `CERTIFICATE_DOWNLOADS_ENABLED`, release-date banner, 48h announcement.
- Price: default 15,000 TZS (per-template override). Payment via Snippe (`CertificatePayment`).
- Verification: public `verify_certificate` page, HMAC-signed URLs, QR codes, optional expiry.

### 6.6 AI Chatbot
- Cerebras-backed, identity-locked ("ChuoSmart AI Lecturer"), logs messages, session history for guests, JSON API endpoint.

### 6.7 Job Portal
- Users/companies post jobs; visibility gated by `UserJobApproval` + company verification.
- External job ingestion from Ajira (scraper) + optional LinkedIn/Indeed/Adzuna/BrighterMonday.
- Apply with resume upload, employer pipeline (pending→hired), saved jobs, search preferences + email notifications.
- AI course recommendations per job (cached).

### 6.8 Affiliate Program
- Users register as affiliates, get referral code, share `/ref/<username>/` or `?ref=CODE`.
- Clicks tracked, commission 10% on purchases, payout requests processed by admin/command.

### 6.9 Newsletter & Notifications
- Daily newsletter digest with category selection, per-subscriber dedupe logs, admin test sends, unsubscribe via token.
- `User.newsletter` property toggle; `newsletter_settings` view.
- Web push notifications via `django-webpush`; helper views in core.

### 6.10 SEO
- Dynamic sitemaps (products, blogs, jobs, static pages), `robots.txt`, canonical-domain middleware (www→non-www), trailing-slash enforcement, SEO context processors, per-page meta.

---

## 7. Configuration (Settings Highlights)

**From `.env`** (loaded via `python-dotenv`): `SECRET_KEY`, `DJANGO_DEBUG`, `DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT`, `CEREBRAS_API_KEY`, `SNIPPE_API_KEY`, `SNIPPE_WEBHOOK_SECRET`, `CERTIFICATE_SIGNING_SECRET`, `CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET`, `VAPID_*`, `SUPPORT_EMAIL_HOST_PASSWORD`, `NEWSLETTER_*`, `JOBS_MAINTENANCE_TOKEN`.

**Key settings:**
- `ALLOWED_HOSTS`: localhost, chuosmart.com, www, mail, ngrok
- `CSRF_TRUSTED_ORIGINS`: localhost, www/root domain, ngrok
- DB: MySQL utf8mb4 with STRICT_TRANS_TABLES; test charset utf8mb4_unicode_ci
- Sessions: DB-backed, 1-year age, never expire on browser close, HTTPOnly, Secure in prod; idle timeout effectively disabled
- `CEREBRAS_ASSESSMENT_MODEL = 'zai-glm-4.7'`, max tokens 4000, context limit 12000, strict assessments default True
- `CERTIFICATE_DOWNLOADS_ENABLED = True`, `CERTIFICATE_RELEASE_DATE = 2026-06-24`, `CERTIFICATE_PRICE = 15000`
- Email: SMTP host `server311.web-hosting.com:465` SSL
- Logging: rotating file handlers → `logs/email.log`, `logs/lms.log` (+console)
- Security (prod only): HSTS, XSS filter, nosniff, SSL redirect, secure cookies, `X_FRAME_OPTIONS=DENY`; custom `CSRF_FAILURE_VIEW`
- TinyMCE: CDN 5.10.7, Cloudinary image upload endpoint, custom CSS

**Middleware order:** Security → Session → WhiteNoise → CanonicalDomain → TrailingSlash → Common → CSRF → Auth → Messages → XFrame → SecurityHeaders → SessionIdleTimeout. (Affiliates `ReferralMiddleware` is not registered globally — it lives in the app; referral handling is via URL paths.)

---

## 8. Management Commands (cron/ops surface)

**core:** `send_daily_newsletter`, `populate_subscriptions`, `convert_to_webp`, `fix_blog_content`, `fix_blog_content_advanced`, `cleanup_all_blog_content`, `vapid_key`, `generate_vapid_keys`, `fix_charset`, `update_site_domain`

**lms:** `process_quiz_generation_jobs`, `queue_all_module_quizzes`, `regenerate_all_quizzes`, `import_quizzes`, `export_quizzes`, `sync_lms_profiles`, `create_dev_demo_course`, `audit_certificate_payments`, `fallback_pending_quiz_jobs`

**jobs:** `fetch_jobs`, `fetch_ajira_jobs`, `delete_ajira_jobs`, `seed_dummy_jobs`, `populate_skills`, `populate_industries`

**affiliates:** `process_payouts`

---

## 9. Tests & Quality

- Per-app `tests.py` (core, lms, affiliates, materials, jobs) and `jobs/tests/` package.
- `Commerce/test_settings.py` for isolated test DB config.
- Several root-level helper scripts exist (`check_user.py`, `debug_jobs.py`, `debug_module.py`, `mark_course_complete.py`, `mark_existing_quizzes.py`, `run_migration.py`) — ad-hoc dev tools, not part of test suite.
- Many ops shell scripts in repo root (`fix_*`, `install_all_requirements.sh`) — historical one-off fixes.

---

## 10. Deployment / Ops Notes

- Deployed to a **shared hosting (cPanel)**-style environment: MySQL + Gunicorn + WhiteNoise, no Docker.
- Scheduler removed (APScheduler caused migrations issues on cPanel) → DB-backed queues + uptime-robot maintenance hits.
- Media: Cloudinary for images, but local `media/` still supported (dual `Blog` thumbnail fields).
- `SESSION_ENGINE` = db (works on shared hosting).
- Historical fix scripts at repo root indicate past MySQL charset/migration struggles (emoji support, `utf8mb4`).

---

## 11. Known Issues / Observations (for prompt generation)

1. **Duplicate/legacy model files**: `lms/models.py` vs `lms/models/models.py` — the latter is the active one (contains the newer fields); the former appears outdated and could be removed. Verify before refactoring.
2. **README.md is stale** — still describes the original e-commerce starter template, not ChuoSmart's actual features.
3. **`CERTIFICATE_ANNOUNCEMENT_START`** is set to `2026-06-25` — a one-time banner; timestamp may need re-setting for future announcements.
4. **Hardcoded/dead config** in settings: commented-out SQLite/Postgres/Neon DB blocks; ngrok host in `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`; commented CSRF cookie lines.
5. **Marketplace has no online payment** (only LMS has Snippe). Order flow is manual.
6. **`core/middleware.py` + `core/canonicalization.py`** split security vs URL logic; `affiliates/middleware.py` is defined but referral flow also served by `affiliates:referral_link` URL routes — potential duplicate/untested path.
7. **`jobs/scheduler.py`** is vestigial (APScheduler removed).
8. **Pillow commented out** in requirements but used for WebP/QR; confirm installed in prod.
9. `debug_upload_view` and `debug_upload` URL exist in LMS ("remove in production" comment).
10. Test coverage is thin relative to the size of `lms/views.py` (~3500 lines) and `jobs/api_integration.py`.
11. `LOGIN_URL = 'login'` is the core login name; `admin/` still uses its own.
12. Certificate downloads gated by payment; `admin_granted_certificate`/`certificate_prepaid` fields allow free issuance paths.
13. `.env` holds secrets (DB, AI keys, Snippe, Cloudinary) — never commit it.
14. `Product.price`, `OrderPlaced.price`, etc. use `FloatField`/`CharField` in core (money stored as float — a known anti-pattern; LMS uses Decimal).
15. `SubscriptionPayment` (manual proof upload) vs Snippe — legacy dual payment approach exists in core marketplace for subscription upgrades.

---

## 12. Suggested Next Steps for the Developer

- Add proper test coverage for payment webhook idempotency and module-access gating.
- Add test coverage for materials permissions and newsletter digest categories.
- Consolidate the two `lms/models*` files.
- Move secrets fully to env; remove commented DB configs.
- Consider `django-money` or Decimal for marketplace prices.
- Add Dockerfile / CI for reproducible deploys.
