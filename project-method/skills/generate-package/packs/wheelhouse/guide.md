# Wheelhouse guide

What a project built on Wheelhouse data needs to know. Facts were last checked on 2026-10-28 against the published API documentation and a live account. **The API is in beta:** when the live documentation or real data differs from this guide, they win. Write the difference under "Gotchas" in the project's `CLAUDE.md` and tell the owner.

## 1. Where to look things up

In this order:
1. **Real data.** Through the Wheelhouse connector in Claude, if connected (read only): the only sure way to see a field's real shape. Several replies are marked as open-ended in the published schema but are fully structured in practice.
2. **The API documentation:** `https://api.usewheelhouse.com/wheelhouse_rm_api`. Endpoints, parameters, replies, error codes.
3. **The connector's own tool descriptions.** Each Wheelhouse tool (named `wheelhouse_rm…`) describes what it does and often names its API path, plus details the documentation leaves out (how overlapping rates behave, confirmation needs).
4. **Wheelhouse's other skills in Claude**, if the person has any: they carry tested how-tos for specific jobs (pacing reports, custom-rate changes). Claude sees what is installed; use what fits.
5. **Wheelhouse support** (`support@usewheelhouse.com`) for account questions: API access, key scope, whether the account has a test listing.

Never guess a field name or behavior. Say which of these you checked.

## 2. How the project gets its data

There are two ways in (Claude's Wheelhouse connector, or the RM API with a key). Which one a project uses follows from its **shape**, which the interview settles from the person's answers (Q-CONNECT-3, `references/shape.md`), never from how technical they seem, and which the owner has the final say on. This table is what each shape means for Wheelhouse data (the shapes and tiers are in `references/shape.md`).

| | With Claude, when asked | A page a team uses | Claude refreshes it on a schedule | Software that runs without Claude |
|---|---|---|---|---|
| How it works | Claude reads Wheelhouse through the connector while the person is there: reports, checks, one-off changes | Claude builds a page (a Claude artifact: a web page kept in their Claude account that they can share), reads Wheelhouse through the owner's connector, and saves a copy into the page. Everyone it is shared with searches, sorts and filters that copy | The same page or report; a scheduled Claude task does the refresh (for example every morning) instead of the owner asking | A website, app or script calls the RM API with a key, on a schedule or whenever someone opens it, with no Claude involved |
| Signs in with | The person's Wheelhouse account, through the connector's own sign-in | The owner's connector, used by Claude only. People it is shared with need no Wheelhouse connection | The owner's connector, used by the scheduled task. No key | An RM API key, sent in the `X-Integration-Api-Key` header to `https://api.usewheelhouse.com/ss_api/v1` |
| How fresh | Whenever they ask | Whenever the owner asks Claude to refresh it ("refresh my Pace Watch page") | On the schedule, while the owner's computer is on | On its own schedule, whatever the owner's computer is doing |
| Where it's built | Anywhere | Anywhere, the website included | Cowork | Cowork or Claude Code, plus somewhere for it to run (their computer, a server, a host like Vercel) |
| The answers that point here | Just them, when they ask | Others need to look at it, and "when I ask" is fresh enough | Fresh every day with nobody asking; depending on the owner's computer is fine | It must not depend on Claude or the owner's computer, feed another system, or be used by people outside Claude |

When nothing in the answers points further, the simplest that fits. If a later request meets the brief's "Check again if" (for example "can it update itself every morning?"), raise it as a decision (`references/shape.md`). Moving up keeps the plan: a scheduled refresh adds the scheduled task and a check that it ran; software adds the key story (Story B) and the stories for the website, app or script.

### A page a team uses: what was seen (one account, 2026-11-03)

Seen once, on a Wheelhouse staff account, with a test page. These are behaviors of Claude's platform, which can change: treat them like the API facts in this guide, and check again (a quick test page) before a project depends on one.

- **Claude refreshing a saved copy worked.** Claude read Wheelhouse in the chat and wrote the copy into the page's shared storage; the page only read that copy. A viewer in the same company and an outside personal Claude account invited by email both saw it without connecting Wheelhouse, and a refresh reached their open pages within about 30 seconds, without reloading.
- **A page using the connector runs as the person viewing it,** with their own Wheelhouse login. Sharing the page did not share the owner's access.
- **A page that read the connector and saved what it found for others to see was refused** by the organization's Claude settings ("blocked by policy"). The likely reason is copying connector data where others can see it; Claude did not say which setting.
- **The connector offered a page only one general "run this" tool,** so allowing a page to use it lets the page do anything the connector can, changes included.
- **Sharing outside the company** worked on that account; it depends on each Claude plan's admin settings.

### Building a team page (the advice that follows)

- **The page never connects to Wheelhouse itself** (rule 7 in `references/wheelhouse.md`): Claude refreshes the saved copy when the owner asks. The pack's Story E builds it.
- **Who can change the copy:** set the page's storage so everyone can read the copy and only the owner (and anyone they make an editor) can replace it. People it is shared with change only their own view (search, sort, filters).
- **A live page just for the owner** may use the connector directly, after the owner has been told plainly that allowing it covers changes too; its code only reads, and Claude shows the owner what it sends.
- **It works in chat or in Cowork:** the page lives in the person's Claude account, not in the project folder.

### The API key ("On its own")

- **The key** is made in the Wheelhouse account (Account → API Key). It opens the whole account, so treat it like a bank password: in a private file in the project, listed in the rules as never shared, never in the chat, the log, a screenshot or anything that goes online; read only by code that runs on the person's computer or server, never sent to a phone or browser.
- **Read-only keys exist.** They allow reading (and the non-changing preview) and refuse every change with `403`. A project that only reads should ask for one.
- A project often uses both: the connector to look at real data while planning, then the API for the finished tool. The connector's replies match the API's, so what was seen through it holds.

## 3. Finding a listing, pages and limits

- **A listing is named by two values together, always:** `listing_id` and `channel`, both from `GET /listings`. Either the channel's own ID with its channel (for example `airbnb`), unique only inside that channel; or the listing's `wheelhouse_id` with the channel written as `wheelhouse`, unique across the account. Mixing them gives `404`. Fetch the listings once at the start and keep the list, rather than looking each one up again.
- **Pages:** list endpoints take `page` (from 1) and `per_page` (100 at most), or `offset`, never both. Keep asking until a page comes back with fewer than `per_page` items.
- **Request limits:** every reply carries `X-RateLimit-Limit`, `X-RateLimit-Remaining` and `X-RateLimit-Reset`; read the limit from there and never write a number into the project (it has changed before). On `429`, wait for `Retry-After` if given, otherwise back off (1s, 2s, 4s … up to about a minute, with a little randomness).
- **Prefer the bulk endpoints** whenever many listings are involved: `GET /listings/kpis` ranks the whole portfolio by one measure in one call; preferences and custom rates have bulk forms. Never loop a single-listing call over the whole portfolio.

## 4. Reading: what lives where, and the surprises

| The project needs | Endpoint |
|---|---|
| The listings, their names, locations, bedrooms, currency | `GET /listings` |
| Rolling numbers (revenue, occupancy, ADR, lead time, pickup, RevPAR, comp-set figures) for the next or last 7–365 days | `GET /listings/{id}/kpis`, one listing; `GET /listings/kpis`, the portfolio ranked by one measure |
| Monthly, quarterly or yearly numbers, past and future | `GET /listings/{id}/kpis/monthly` (`/quarterly`, `/yearly`) |
| Price and availability per night | `GET /listings/{id}/price_calendar` (and its siblings: `last_posted_prices`, `min_max_prices`, `min_stay_calendar`) |
| Reservations | `GET /listings/{id}/reservations`, filtered by stay date (default) or booked date |
| Settings (base price, seasonality, minimums, rules) | `GET /preferences/{id}` |
| Date-specific price overrides | `GET /listings/{id}/custom_rates` |
| What changed and when | `GET /preferences/{id}/changelog` (despite the name, it includes custom-rate changes) |

Surprises seen in real data:
- **Multi-unit listings.** A listing with `number_of_active_units` greater than 1 is several bookable units. Single-unit listings report `1`, not empty, so test "greater than 1", never "has a value". Per-night endpoints return one row per unit per night with a `unit_number`; treat it as a label, not a count. Live data started at 0, not 1 as documented, and can have gaps. Take the list of units from the rows; settings and overrides apply to the whole listing.
- **Custom-rate rows read back slimmer than documented:** no `id`, no expiry or timestamps, and numbers as decimals. Don't depend on those fields from a read.
- **"This time last year" has no single endpoint.** Work it out from the monthly numbers, or from reservations booked on or before the same date a year ago. Decide which with the owner and write the method down; it is a definition the numbers rest on.
- **No value is not zero.** A measure not yet worked out comes back empty; show it as missing, not as 0.
- **Money is in the listing's currency.** Never add amounts across currencies; group by currency.
- `supported_settings` on a listing says which settings its channel takes. A setting it doesn't support is silently ignored on a change.

## 5. Changing things: the two kinds, and how each behaves

Wheelhouse has two ways to change a price, and they behave differently. Confirm with the owner which one they mean before planning either.
- **Settings (preferences):** rules that shape what Wheelhouse recommends from now on (base price, seasonality, day of week, minimum and maximum price, minimum stay …). Rules of a kind follow an order: global, then day of week or monthly, then time-based, seasonal, event, (gap and adjacency, minimum stay only), and custom last, which wins.
- **Custom rates:** a price for specific dates that overrides the recommendation outright.

The surprises:
- **A settings change replaces each list of rules whole.** `PUT /preferences/{id}` leaves top-level settings you leave out alone, but any list of rules you send (for example `minimum_price_rules_v3`, `minimum_stay_rules_v3`, `maximum_price_rules_v3`) replaces the existing list completely. Always fetch the settings immediately before, keep every rule you're not changing, and send the full list. Sending only the new rule deletes all the others, with no error.
- **Preview first:** `POST /preferences/{id}/preview` shows what a settings change would do, without changing anything.
- **A new custom rate silently trims, splits or replaces** any existing rate on the same dates. Fetch them first, and tell the owner exactly which existing rates will be shortened, split or replaced.
- **Rates don't add up by themselves.** Two kinds: `fixed` (a price per night) and `adjustment` (a percentage of the recommendation, 100 = no change). To add on top of an existing rate, the project works out the new value itself, and the two kinds combine in opposite ways:
  - adjustment: add the points (110 plus 10 more is 120, not 110 × 1.10);
  - fixed: multiply the price ($100 plus 10% is $110).
  Never use one kind's formula for the other. Pin both with tests that name the direction.
- **Custom-rate values are whole numbers, 1 or more.**
- **Several ranges at once** go to the bulk path `/listings/{id}/bulk_custom_rates`, which reports per range: `207` means some failed, `424` all. (Check this path against the live documentation before relying on it: one older how-to gave a different one.)
- **Removing a custom rate** returns those dates to Wheelhouse's recommended price, not to empty. Say so before removing.
- **Notes and the changelog** give a record of what was changed; offer to write a short Wheelhouse note with each change the project makes.

## 6. Reading the reply after a change

A `200` alone is not proof:
- Every settings reply has a `warnings` list. Anything in it is something that didn't take effect; show it to the owner.
- `207` from a bulk call means some parts failed: report each part.
- Then read the listing back and compare with what was sent.

Error codes to handle one by one: `401` key missing or wrong; `403` not allowed (or a read-only key trying to change); `404` not found (also what an inaccessible listing returns under channel `wheelhouse`); `409` another request for that listing is still running, try again after it; `422` the values were refused; `423` not ready yet (recommendations still generating), try again shortly; `429` too many requests.

## 7. Testing without touching real listings

- Build and test reading and change-planning on made-up data first, shaped like the real replies seen in §4.
- The first real change goes to one listing: a test listing if the account has one (ask Wheelhouse if unsure), otherwise one the owner chooses. Check it, then wider, each with its own yes (`references/wheelhouse.md`).
- A project that changes things checks, in code, that every change goes to a listing the owner has allowed, before anything is sent: one checked doorway (`references/safety-patterns.md`).
