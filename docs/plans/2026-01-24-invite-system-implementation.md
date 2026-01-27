# Invite System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement "Invite a Friend" loyalty reward system for VPN service

**Architecture:** Node.js + PostgreSQL + Telegraf bot. InviteService handles core logic, integrates with existing payment flow and referral system. Cron jobs for automation.

**Tech Stack:** Node.js, PostgreSQL 17, Telegraf (Telegram bot), Express (API), node-cron

---

## Task 1: Database Migration - Core Tables

**Files:**
- Create: `migrations/20260124000001_create_invite_tables.sql`

**Step 1: Create migration file with all tables**

```sql
-- migrations/20260124000001_create_invite_tables.sql

-- Invite rules: which subscription gives how many invites
CREATE TABLE invite_rules (
    id SERIAL PRIMARY KEY,
    subscription_type VARCHAR(50) NOT NULL,  -- '1_month', '3_months', '6_months', '12_months'
    invites_count INTEGER NOT NULL DEFAULT 0,
    friend_days INTEGER NOT NULL DEFAULT 30,
    friend_discount INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(subscription_type)
);

-- Global invite settings
CREATE TABLE invite_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Invite promotions (time-limited multipliers)
CREATE TABLE invite_promotions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    multiplier DECIMAL(3,1) NOT NULL DEFAULT 1.0,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    subscription_types VARCHAR(50)[] DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Individual invites
CREATE TABLE invites (
    id SERIAL PRIMARY KEY,
    owner_id INTEGER NOT NULL,
    code VARCHAR(20) NOT NULL UNIQUE,
    friend_days INTEGER NOT NULL,
    friend_discount INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'available',
    used_by INTEGER,
    used_at TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT invites_status_check CHECK (status IN ('available', 'used', 'expired'))
);

-- Manual access grants by admin
CREATE TABLE manual_access_grants (
    id SERIAL PRIMARY KEY,
    admin_telegram_id BIGINT NOT NULL,
    user_telegram_id BIGINT NOT NULL,
    days INTEGER NOT NULL,
    grant_type VARCHAR(50) NOT NULL,
    note TEXT,
    traffic_limit_gb INTEGER,
    device_limit INTEGER NOT NULL DEFAULT 1,
    node_access VARCHAR(20) NOT NULL DEFAULT 'all',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    activated_at TIMESTAMP,
    expires_at TIMESTAMP,
    CONSTRAINT grant_type_check CHECK (grant_type IN ('partner', 'compensation', 'friend', 'test'))
);

-- Indexes
CREATE INDEX idx_invites_owner_status ON invites(owner_id, status);
CREATE INDEX idx_invites_code ON invites(code);
CREATE INDEX idx_invites_expires_at ON invites(expires_at) WHERE status = 'available';
CREATE INDEX idx_manual_grants_user ON manual_access_grants(user_telegram_id);

-- Default settings
INSERT INTO invite_settings (key, value) VALUES
    ('max_invites_per_user', '3'),
    ('invite_expiry_days', '90'),
    ('reminder_interval_days', '14'),
    ('expiry_warning_days', '7');

-- Default rules (adjust as needed)
INSERT INTO invite_rules (subscription_type, invites_count, friend_days, friend_discount) VALUES
    ('1_month', 0, 0, 0),
    ('3_months', 0, 0, 0),
    ('6_months', 1, 14, 10),
    ('12_months', 1, 30, 15);
```

**Step 2: Run migration**

```bash
psql -h localhost -U vpn_user -d vpn_db -f migrations/20260124000001_create_invite_tables.sql
```

Expected: Tables created, no errors

**Step 3: Verify tables exist**

```bash
psql -h localhost -U vpn_user -d vpn_db -c "\dt invite*"
```

Expected: List of 4 tables (invite_rules, invite_settings, invite_promotions, invites)

**Step 4: Commit**

```bash
git add migrations/20260124000001_create_invite_tables.sql
git commit -m "feat(db): add invite system tables"
```

---

## Task 2: Invite Model

**Files:**
- Create: `src/models/invite.js`
- Create: `src/models/index.js` (if not exists)

**Step 1: Create invite model**

```javascript
// src/models/invite.js
const { pool } = require('../config/database');
const crypto = require('crypto');

class Invite {
    static generateCode() {
        const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
        let code = 'INV-';
        for (let i = 0; i < 6; i++) {
            code += chars.charAt(crypto.randomInt(chars.length));
        }
        return code;
    }

    static async create({ ownerId, friendDays, friendDiscount, expiresAt }) {
        const code = this.generateCode();
        const result = await pool.query(
            `INSERT INTO invites (owner_id, code, friend_days, friend_discount, expires_at)
             VALUES ($1, $2, $3, $4, $5)
             RETURNING *`,
            [ownerId, code, friendDays, friendDiscount, expiresAt]
        );
        return result.rows[0];
    }

    static async findByCode(code) {
        const result = await pool.query(
            'SELECT * FROM invites WHERE code = $1',
            [code.toUpperCase()]
        );
        return result.rows[0];
    }

    static async findByOwner(ownerId, status = null) {
        let query = 'SELECT * FROM invites WHERE owner_id = $1';
        const params = [ownerId];

        if (status) {
            query += ' AND status = $2';
            params.push(status);
        }

        query += ' ORDER BY created_at DESC';
        const result = await pool.query(query, params);
        return result.rows;
    }

    static async countByOwner(ownerId, status = 'available') {
        const result = await pool.query(
            'SELECT COUNT(*) FROM invites WHERE owner_id = $1 AND status = $2',
            [ownerId, status]
        );
        return parseInt(result.rows[0].count, 10);
    }

    static async markUsed(id, usedBy) {
        const result = await pool.query(
            `UPDATE invites
             SET status = 'used', used_by = $2, used_at = NOW()
             WHERE id = $1
             RETURNING *`,
            [id, usedBy]
        );
        return result.rows[0];
    }

    static async markExpired(id) {
        const result = await pool.query(
            `UPDATE invites SET status = 'expired' WHERE id = $1 RETURNING *`,
            [id]
        );
        return result.rows[0];
    }

    static async getExpiringSoon(days) {
        const result = await pool.query(
            `SELECT * FROM invites
             WHERE status = 'available'
             AND expires_at BETWEEN NOW() AND NOW() + INTERVAL '1 day' * $1`,
            [days]
        );
        return result.rows;
    }

    static async expireOld() {
        const result = await pool.query(
            `UPDATE invites
             SET status = 'expired'
             WHERE status = 'available' AND expires_at < NOW()
             RETURNING *`
        );
        return result.rows;
    }
}

module.exports = Invite;
```

**Step 2: Commit**

```bash
git add src/models/invite.js
git commit -m "feat(models): add Invite model"
```

---

## Task 3: Invite Rule Model

**Files:**
- Create: `src/models/inviteRule.js`

**Step 1: Create invite rule model**

```javascript
// src/models/inviteRule.js
const { pool } = require('../config/database');

class InviteRule {
    static async findBySubscription(subscriptionType) {
        const result = await pool.query(
            'SELECT * FROM invite_rules WHERE subscription_type = $1 AND is_active = true',
            [subscriptionType]
        );
        return result.rows[0];
    }

    static async findAll() {
        const result = await pool.query(
            'SELECT * FROM invite_rules ORDER BY subscription_type'
        );
        return result.rows;
    }

    static async update(id, { invitesCount, friendDays, friendDiscount, isActive }) {
        const result = await pool.query(
            `UPDATE invite_rules
             SET invites_count = COALESCE($2, invites_count),
                 friend_days = COALESCE($3, friend_days),
                 friend_discount = COALESCE($4, friend_discount),
                 is_active = COALESCE($5, is_active),
                 updated_at = NOW()
             WHERE id = $1
             RETURNING *`,
            [id, invitesCount, friendDays, friendDiscount, isActive]
        );
        return result.rows[0];
    }

    static async create({ subscriptionType, invitesCount, friendDays, friendDiscount }) {
        const result = await pool.query(
            `INSERT INTO invite_rules (subscription_type, invites_count, friend_days, friend_discount)
             VALUES ($1, $2, $3, $4)
             ON CONFLICT (subscription_type) DO UPDATE SET
                 invites_count = $2,
                 friend_days = $3,
                 friend_discount = $4,
                 updated_at = NOW()
             RETURNING *`,
            [subscriptionType, invitesCount, friendDays, friendDiscount]
        );
        return result.rows[0];
    }
}

module.exports = InviteRule;
```

**Step 2: Commit**

```bash
git add src/models/inviteRule.js
git commit -m "feat(models): add InviteRule model"
```

---

## Task 4: Invite Settings Model

**Files:**
- Create: `src/models/inviteSetting.js`

**Step 1: Create settings model**

```javascript
// src/models/inviteSetting.js
const { pool } = require('../config/database');

class InviteSetting {
    static async get(key, defaultValue = null) {
        const result = await pool.query(
            'SELECT value FROM invite_settings WHERE key = $1',
            [key]
        );
        if (result.rows.length === 0) {
            return defaultValue;
        }
        return JSON.parse(result.rows[0].value);
    }

    static async set(key, value) {
        const result = await pool.query(
            `INSERT INTO invite_settings (key, value, updated_at)
             VALUES ($1, $2, NOW())
             ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = NOW()
             RETURNING *`,
            [key, JSON.stringify(value)]
        );
        return result.rows[0];
    }

    static async getAll() {
        const result = await pool.query('SELECT * FROM invite_settings');
        const settings = {};
        for (const row of result.rows) {
            settings[row.key] = JSON.parse(row.value);
        }
        return settings;
    }

    // Convenience methods
    static async getMaxInvitesPerUser() {
        return await this.get('max_invites_per_user', 3);
    }

    static async getInviteExpiryDays() {
        return await this.get('invite_expiry_days', 90);
    }

    static async getReminderIntervalDays() {
        return await this.get('reminder_interval_days', 14);
    }

    static async getExpiryWarningDays() {
        return await this.get('expiry_warning_days', 7);
    }
}

module.exports = InviteSetting;
```

**Step 2: Commit**

```bash
git add src/models/inviteSetting.js
git commit -m "feat(models): add InviteSetting model"
```

---

## Task 5: Invite Promotion Model

**Files:**
- Create: `src/models/invitePromotion.js`

**Step 1: Create promotion model**

```javascript
// src/models/invitePromotion.js
const { pool } = require('../config/database');

class InvitePromotion {
    static async getActive(subscriptionType = null) {
        let query = `
            SELECT * FROM invite_promotions
            WHERE is_active = true
            AND start_date <= NOW()
            AND end_date >= NOW()
        `;
        const params = [];

        if (subscriptionType) {
            query += ` AND ($1 = ANY(subscription_types) OR subscription_types = '{}')`;
            params.push(subscriptionType);
        }

        const result = await pool.query(query, params);
        return result.rows;
    }

    static async getMultiplier(subscriptionType) {
        const promos = await this.getActive(subscriptionType);
        if (promos.length === 0) return 1.0;

        // Return highest multiplier if multiple promos active
        return Math.max(...promos.map(p => parseFloat(p.multiplier)));
    }

    static async create({ name, multiplier, startDate, endDate, subscriptionTypes }) {
        const result = await pool.query(
            `INSERT INTO invite_promotions (name, multiplier, start_date, end_date, subscription_types)
             VALUES ($1, $2, $3, $4, $5)
             RETURNING *`,
            [name, multiplier, startDate, endDate, subscriptionTypes || []]
        );
        return result.rows[0];
    }

    static async update(id, { name, multiplier, startDate, endDate, subscriptionTypes, isActive }) {
        const result = await pool.query(
            `UPDATE invite_promotions SET
                name = COALESCE($2, name),
                multiplier = COALESCE($3, multiplier),
                start_date = COALESCE($4, start_date),
                end_date = COALESCE($5, end_date),
                subscription_types = COALESCE($6, subscription_types),
                is_active = COALESCE($7, is_active)
             WHERE id = $1
             RETURNING *`,
            [id, name, multiplier, startDate, endDate, subscriptionTypes, isActive]
        );
        return result.rows[0];
    }

    static async findAll() {
        const result = await pool.query(
            'SELECT * FROM invite_promotions ORDER BY start_date DESC'
        );
        return result.rows;
    }

    static async delete(id) {
        await pool.query('DELETE FROM invite_promotions WHERE id = $1', [id]);
    }
}

module.exports = InvitePromotion;
```

**Step 2: Commit**

```bash
git add src/models/invitePromotion.js
git commit -m "feat(models): add InvitePromotion model"
```

---

## Task 6: Manual Access Grant Model

**Files:**
- Create: `src/models/manualAccessGrant.js`

**Step 1: Create manual grant model**

```javascript
// src/models/manualAccessGrant.js
const { pool } = require('../config/database');

class ManualAccessGrant {
    static async create({
        adminTelegramId,
        userTelegramId,
        days,
        grantType,
        note,
        trafficLimitGb,
        deviceLimit,
        nodeAccess
    }) {
        const expiresAt = new Date();
        expiresAt.setDate(expiresAt.getDate() + days);

        const result = await pool.query(
            `INSERT INTO manual_access_grants
             (admin_telegram_id, user_telegram_id, days, grant_type, note,
              traffic_limit_gb, device_limit, node_access, activated_at, expires_at)
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), $9)
             RETURNING *`,
            [adminTelegramId, userTelegramId, days, grantType, note,
             trafficLimitGb, deviceLimit || 1, nodeAccess || 'all', expiresAt]
        );
        return result.rows[0];
    }

    static async findByUser(userTelegramId) {
        const result = await pool.query(
            `SELECT * FROM manual_access_grants
             WHERE user_telegram_id = $1
             ORDER BY created_at DESC`,
            [userTelegramId]
        );
        return result.rows;
    }

    static async findActive(userTelegramId) {
        const result = await pool.query(
            `SELECT * FROM manual_access_grants
             WHERE user_telegram_id = $1
             AND expires_at > NOW()
             ORDER BY expires_at DESC
             LIMIT 1`,
            [userTelegramId]
        );
        return result.rows[0];
    }

    static async getStats(fromDate, toDate) {
        const result = await pool.query(
            `SELECT
                grant_type,
                COUNT(*) as count,
                SUM(days) as total_days
             FROM manual_access_grants
             WHERE created_at BETWEEN $1 AND $2
             GROUP BY grant_type`,
            [fromDate, toDate]
        );
        return result.rows;
    }

    static async findAll(limit = 50, offset = 0) {
        const result = await pool.query(
            `SELECT * FROM manual_access_grants
             ORDER BY created_at DESC
             LIMIT $1 OFFSET $2`,
            [limit, offset]
        );
        return result.rows;
    }
}

module.exports = ManualAccessGrant;
```

**Step 2: Commit**

```bash
git add src/models/manualAccessGrant.js
git commit -m "feat(models): add ManualAccessGrant model"
```

---

## Task 7: Invite Service - Core Logic

**Files:**
- Create: `src/services/inviteService.js`

**Step 1: Create invite service**

```javascript
// src/services/inviteService.js
const Invite = require('../models/invite');
const InviteRule = require('../models/inviteRule');
const InviteSetting = require('../models/inviteSetting');
const InvitePromotion = require('../models/invitePromotion');
const ManualAccessGrant = require('../models/manualAccessGrant');

class InviteService {
    constructor(bot, userService, subscriptionService) {
        this.bot = bot;
        this.userService = userService;
        this.subscriptionService = subscriptionService;
    }

    /**
     * Grant invites after successful payment
     */
    async grantInvites(userId, telegramId, subscriptionType) {
        // 1. Get rule for this subscription
        const rule = await InviteRule.findBySubscription(subscriptionType);
        if (!rule || rule.invites_count === 0) {
            return { granted: 0, reason: 'no_rule' };
        }

        // 2. Check promotion multiplier
        const multiplier = await InvitePromotion.getMultiplier(subscriptionType);
        let count = Math.floor(rule.invites_count * multiplier);

        // 3. Check user limit
        const maxInvites = await InviteSetting.getMaxInvitesPerUser();
        const currentInvites = await Invite.countByOwner(userId, 'available');

        if (currentInvites >= maxInvites) {
            return { granted: 0, reason: 'limit_reached' };
        }

        const slotsAvailable = maxInvites - currentInvites;
        count = Math.min(count, slotsAvailable);

        // 4. Calculate expiry date
        const expiryDays = await InviteSetting.getInviteExpiryDays();
        const expiresAt = new Date();
        expiresAt.setDate(expiresAt.getDate() + expiryDays);

        // 5. Create invites
        const invites = [];
        for (let i = 0; i < count; i++) {
            const invite = await Invite.create({
                ownerId: userId,
                friendDays: rule.friend_days,
                friendDiscount: rule.friend_discount,
                expiresAt
            });
            invites.push(invite);
        }

        // 6. Notify user
        if (invites.length > 0) {
            await this.notifyInvitesGranted(telegramId, invites, rule.friend_days);
        }

        return { granted: invites.length, invites };
    }

    /**
     * Activate invite by friend
     */
    async activateInvite(code, friendTelegramId) {
        // 1. Find invite
        const invite = await Invite.findByCode(code);
        if (!invite) {
            throw new Error('INVITE_NOT_FOUND');
        }

        if (invite.status !== 'available') {
            throw new Error('INVITE_ALREADY_USED');
        }

        if (invite.expires_at && new Date(invite.expires_at) < new Date()) {
            await Invite.markExpired(invite.id);
            throw new Error('INVITE_EXPIRED');
        }

        // 2. Get or create friend user
        let friendUser = await this.userService.findByTelegramId(friendTelegramId);
        if (!friendUser) {
            friendUser = await this.userService.create({
                telegramId: friendTelegramId,
                source: 'invite'
            });
        }

        // 3. Check if friend already has active subscription
        const hasActive = await this.subscriptionService.hasActiveSubscription(friendUser.id);
        if (hasActive) {
            throw new Error('ALREADY_HAS_SUBSCRIPTION');
        }

        // 4. Mark invite as used
        await Invite.markUsed(invite.id, friendUser.id);

        // 5. Link as referrer
        await this.userService.setReferrer(friendUser.id, invite.owner_id);

        // 6. Grant free subscription
        const expiresAt = new Date();
        expiresAt.setDate(expiresAt.getDate() + invite.friend_days);

        await this.subscriptionService.grantFreeAccess(friendUser.id, {
            days: invite.friend_days,
            source: 'invite',
            inviteId: invite.id,
            discount: invite.friend_discount
        });

        // 7. Notify both parties
        const owner = await this.userService.findById(invite.owner_id);
        await this.notifyOwnerInviteUsed(owner.telegram_id, friendTelegramId);
        await this.notifyFriendActivated(friendTelegramId, invite.friend_days, invite.friend_discount);

        return { success: true, friendDays: invite.friend_days };
    }

    /**
     * Get user's invites with stats
     */
    async getUserInvites(userId) {
        const invites = await Invite.findByOwner(userId);
        const maxInvites = await InviteSetting.getMaxInvitesPerUser();

        const stats = {
            available: 0,
            used: 0,
            expired: 0,
            convertedToPayment: 0
        };

        for (const invite of invites) {
            stats[invite.status]++;
            if (invite.status === 'used' && invite.used_by) {
                const hasPayment = await this.subscriptionService.hasEverPaid(invite.used_by);
                if (hasPayment) stats.convertedToPayment++;
            }
        }

        return {
            invites,
            stats,
            maxInvites,
            availableSlots: maxInvites - stats.available
        };
    }

    /**
     * Admin: Grant manual access
     */
    async grantManualAccess(adminTelegramId, params) {
        const grant = await ManualAccessGrant.create({
            adminTelegramId,
            ...params
        });

        // Create subscription for user
        await this.subscriptionService.grantFreeAccess(params.userTelegramId, {
            days: params.days,
            source: 'manual_grant',
            grantId: grant.id,
            trafficLimitGb: params.trafficLimitGb,
            deviceLimit: params.deviceLimit,
            nodeAccess: params.nodeAccess
        });

        // Notify user
        await this.notifyManualAccessGranted(params.userTelegramId, params.days);

        return grant;
    }

    // ===== Notification methods =====

    async notifyInvitesGranted(telegramId, invites, friendDays) {
        const invite = invites[0];
        const botUsername = this.bot.botInfo?.username || 'YourVPNBot';

        let message = `🎁 Вы получили ${invites.length > 1 ? invites.length + ' инвайтов' : 'инвайт'} для друга!\n\n`;
        message += `Ваш друг получит ${friendDays} дней бесплатного VPN.\n\n`;
        message += `📋 Код: \`${invite.code}\`\n`;
        message += `🔗 Ссылка: t.me/${botUsername}?start=inv_${invite.code.replace('INV-', '')}\n\n`;
        message += `Используйте /invites чтобы посмотреть все ваши инвайты.`;

        await this.bot.telegram.sendMessage(telegramId, message, { parse_mode: 'Markdown' });
    }

    async notifyOwnerInviteUsed(ownerTelegramId, friendTelegramId) {
        const message = `👋 Ваш друг активировал инвайт и теперь пользуется VPN!\n\n` +
            `Когда друг оплатит подписку, вы получите +7 дней бонуса.`;

        await this.bot.telegram.sendMessage(ownerTelegramId, message);
    }

    async notifyFriendActivated(friendTelegramId, days, discount) {
        let message = `✅ Добро пожаловать!\n\n`;
        message += `Ваш бесплатный доступ активирован на ${days} дней.\n\n`;
        if (discount > 0) {
            message += `🎁 При первой оплате вы получите скидку ${discount}%!\n\n`;
        }
        message += `Используйте /help чтобы узнать как подключить VPN.`;

        await this.bot.telegram.sendMessage(friendTelegramId, message);
    }

    async notifyManualAccessGranted(userTelegramId, days) {
        const message = `✅ Вам предоставлен бесплатный доступ к VPN на ${days} дней!\n\n` +
            `Используйте /help чтобы узнать как подключить VPN.`;

        await this.bot.telegram.sendMessage(userTelegramId, message);
    }

    async notifyExpiringFreeAccess(userTelegramId, daysLeft, discount) {
        let message = `⏰ Ваш бесплатный период заканчивается через ${daysLeft} дня!\n\n`;
        message += `Понравился сервис? Оформите подписку`;
        if (discount > 0) {
            message += ` со скидкой ${discount}%`;
        }
        message += `!\n\n`;
        message += `Используйте /subscribe для оформления подписки.`;

        await this.bot.telegram.sendMessage(userTelegramId, message);
    }

    async notifyInviteExpiringSoon(ownerTelegramId, inviteCode, daysLeft) {
        const message = `⏰ Ваш инвайт ${inviteCode} истечёт через ${daysLeft} дней.\n\n` +
            `Успейте пригласить друга!`;

        await this.bot.telegram.sendMessage(ownerTelegramId, message);
    }
}

module.exports = InviteService;
```

**Step 2: Commit**

```bash
git add src/services/inviteService.js
git commit -m "feat(services): add InviteService with core logic"
```

---

## Task 8: Bot Handlers - User Commands

**Files:**
- Create: `src/handlers/inviteHandlers.js`

**Step 1: Create user invite handlers**

```javascript
// src/handlers/inviteHandlers.js
const { Markup } = require('telegraf');

function setupInviteHandlers(bot, inviteService, userService) {

    // /invites - Show user's invites
    bot.command('invites', async (ctx) => {
        try {
            const user = await userService.findByTelegramId(ctx.from.id);
            if (!user) {
                return ctx.reply('Вы не зарегистрированы. Используйте /start');
            }

            const { invites, stats, maxInvites } = await inviteService.getUserInvites(user.id);
            const botUsername = bot.botInfo?.username || 'YourVPNBot';

            let message = `🎟 Ваши инвайты (${stats.available} из ${maxInvites})\n\n`;

            if (invites.length === 0) {
                message += `У вас пока нет инвайтов.\n`;
                message += `Оплатите подписку на 6 или 12 месяцев, чтобы получить инвайт для друга.`;
            } else {
                const availableInvites = invites.filter(i => i.status === 'available');
                const usedInvites = invites.filter(i => i.status === 'used');

                for (const invite of availableInvites) {
                    const expiresIn = Math.ceil((new Date(invite.expires_at) - new Date()) / (1000 * 60 * 60 * 24));
                    message += `✅ ${invite.code} — доступен\n`;
                    message += `   Срок для друга: ${invite.friend_days} дней\n`;
                    message += `   Истекает через: ${expiresIn} дней\n\n`;
                }

                for (const invite of usedInvites.slice(0, 3)) {
                    message += `☑️ ${invite.code} — использован\n`;
                }

                if (usedInvites.length > 3) {
                    message += `   ...и ещё ${usedInvites.length - 3}\n`;
                }

                message += `\n──────────────────\n`;
                message += `📊 Статистика:\n`;
                message += `Приглашено друзей: ${stats.used}\n`;
                message += `Из них оплатили: ${stats.convertedToPayment}\n`;
            }

            const buttons = [];
            const availableInvite = invites.find(i => i.status === 'available');
            if (availableInvite) {
                buttons.push([
                    Markup.button.callback('📋 Копировать код', `copy_invite_${availableInvite.code}`),
                    Markup.button.callback('🔗 Получить ссылку', `link_invite_${availableInvite.code}`)
                ]);
            }

            await ctx.reply(message, buttons.length > 0 ? Markup.inlineKeyboard(buttons) : {});
        } catch (error) {
            console.error('Error in /invites:', error);
            await ctx.reply('Произошла ошибка. Попробуйте позже.');
        }
    });

    // Callback: Copy invite code
    bot.action(/^copy_invite_(.+)$/, async (ctx) => {
        const code = ctx.match[1];
        await ctx.answerCbQuery();
        await ctx.reply(`📋 Код для друга:\n\n\`${code}\`\n\nОтправьте этот код другу.`, { parse_mode: 'Markdown' });
    });

    // Callback: Get invite link
    bot.action(/^link_invite_(.+)$/, async (ctx) => {
        const code = ctx.match[1];
        const botUsername = bot.botInfo?.username || 'YourVPNBot';
        const shortCode = code.replace('INV-', '');

        await ctx.answerCbQuery();
        await ctx.reply(
            `🔗 Ссылка для друга:\n\nt.me/${botUsername}?start=inv_${shortCode}\n\n` +
            `Отправьте эту ссылку другу — он получит бесплатный VPN!`
        );
    });

    // /invite_link - Quick link for first available invite
    bot.command('invite_link', async (ctx) => {
        try {
            const user = await userService.findByTelegramId(ctx.from.id);
            if (!user) {
                return ctx.reply('Вы не зарегистрированы. Используйте /start');
            }

            const { invites } = await inviteService.getUserInvites(user.id);
            const availableInvite = invites.find(i => i.status === 'available');

            if (!availableInvite) {
                return ctx.reply('У вас нет доступных инвайтов.\nИспользуйте /invites для подробностей.');
            }

            const botUsername = bot.botInfo?.username || 'YourVPNBot';
            const shortCode = availableInvite.code.replace('INV-', '');

            await ctx.reply(
                `🎟 Инвайт для друга (${availableInvite.friend_days} дней бесплатно)\n\n` +
                `📋 Код: \`${availableInvite.code}\`\n` +
                `🔗 Ссылка: t.me/${botUsername}?start=inv_${shortCode}`,
                { parse_mode: 'Markdown' }
            );
        } catch (error) {
            console.error('Error in /invite_link:', error);
            await ctx.reply('Произошла ошибка. Попробуйте позже.');
        }
    });

    // Handle invite activation via deep link
    bot.start(async (ctx, next) => {
        const payload = ctx.startPayload;

        if (payload && payload.startsWith('inv_')) {
            const shortCode = payload.replace('inv_', '');
            const code = `INV-${shortCode}`;

            try {
                const result = await inviteService.activateInvite(code, ctx.from.id);
                // Notification already sent by service
                return;
            } catch (error) {
                const messages = {
                    'INVITE_NOT_FOUND': 'Инвайт не найден. Проверьте код.',
                    'INVITE_ALREADY_USED': 'Этот инвайт уже использован.',
                    'INVITE_EXPIRED': 'Срок действия инвайта истёк.',
                    'ALREADY_HAS_SUBSCRIPTION': 'У вас уже есть активная подписка.'
                };

                const message = messages[error.message] || 'Не удалось активировать инвайт.';
                await ctx.reply(message);
                return;
            }
        }

        // Continue to default start handler
        return next();
    });
}

module.exports = { setupInviteHandlers };
```

**Step 2: Commit**

```bash
git add src/handlers/inviteHandlers.js
git commit -m "feat(handlers): add user invite commands"
```

---

## Task 9: Bot Handlers - Admin Commands

**Files:**
- Create: `src/handlers/adminInviteHandlers.js`

**Step 1: Create admin invite handlers**

```javascript
// src/handlers/adminInviteHandlers.js
const { Markup } = require('telegraf');
const InviteRule = require('../models/inviteRule');
const InviteSetting = require('../models/inviteSetting');
const InvitePromotion = require('../models/invitePromotion');
const Invite = require('../models/invite');
const ManualAccessGrant = require('../models/manualAccessGrant');

function setupAdminInviteHandlers(bot, inviteService, isAdmin) {

    // Middleware to check admin
    const adminOnly = async (ctx, next) => {
        if (!await isAdmin(ctx.from.id)) {
            return ctx.reply('Эта команда доступна только администраторам.');
        }
        return next();
    };

    // /grant_access <user> <days> - Quick grant
    bot.command('grant_access', adminOnly, async (ctx) => {
        const args = ctx.message.text.split(' ').slice(1);

        if (args.length < 2) {
            return ctx.reply(
                'Использование: /grant_access <telegram_id или @username> <дней>\n\n' +
                'Пример: /grant_access @username 30\n' +
                'Пример: /grant_access 123456789 14\n\n' +
                'Для расширенных опций используйте /grant_access_full'
            );
        }

        const userIdentifier = args[0];
        const days = parseInt(args[1], 10);

        if (isNaN(days) || days < 1) {
            return ctx.reply('Количество дней должно быть положительным числом.');
        }

        try {
            // Resolve user telegram ID
            let userTelegramId = userIdentifier;
            if (userIdentifier.startsWith('@')) {
                // Need to resolve username - this requires user to have interacted with bot
                return ctx.reply(
                    'Для выдачи доступа по username, пользователь должен сначала написать боту.\n' +
                    'Используйте Telegram ID вместо username.'
                );
            }

            userTelegramId = parseInt(userTelegramId, 10);
            if (isNaN(userTelegramId)) {
                return ctx.reply('Неверный Telegram ID.');
            }

            await inviteService.grantManualAccess(ctx.from.id, {
                userTelegramId,
                days,
                grantType: 'friend',
                note: `Quick grant by admin`,
                deviceLimit: 3,
                nodeAccess: 'all'
            });

            await ctx.reply(`✅ Доступ на ${days} дней выдан пользователю ${userTelegramId}`);
        } catch (error) {
            console.error('Error in /grant_access:', error);
            await ctx.reply('Ошибка при выдаче доступа: ' + error.message);
        }
    });

    // /grant_access_full - Interactive grant with all options
    bot.command('grant_access_full', adminOnly, async (ctx) => {
        ctx.session = ctx.session || {};
        ctx.session.grantAccess = { step: 'user' };

        await ctx.reply(
            '👤 Введите Telegram ID пользователя:',
            Markup.inlineKeyboard([[Markup.button.callback('❌ Отмена', 'cancel_grant')]])
        );
    });

    // Handle grant_access_full conversation steps
    bot.on('text', async (ctx, next) => {
        if (!ctx.session?.grantAccess) return next();

        const state = ctx.session.grantAccess;

        switch (state.step) {
            case 'user':
                state.userTelegramId = parseInt(ctx.message.text, 10);
                if (isNaN(state.userTelegramId)) {
                    return ctx.reply('Введите корректный Telegram ID (число).');
                }
                state.step = 'days';
                await ctx.reply('📅 Сколько дней доступа выдать?');
                break;

            case 'days':
                state.days = parseInt(ctx.message.text, 10);
                if (isNaN(state.days) || state.days < 1) {
                    return ctx.reply('Введите корректное количество дней.');
                }
                state.step = 'type';
                await ctx.reply(
                    '📋 Выберите тип:',
                    Markup.inlineKeyboard([
                        [Markup.button.callback('🤝 Партнёр', 'grant_type_partner')],
                        [Markup.button.callback('🔧 Компенсация', 'grant_type_compensation')],
                        [Markup.button.callback('👫 Друг', 'grant_type_friend')],
                        [Markup.button.callback('🧪 Тест', 'grant_type_test')]
                    ])
                );
                break;

            case 'note':
                state.note = ctx.message.text;
                state.step = 'confirm';
                await showGrantConfirmation(ctx, state);
                break;
        }
    });

    // Grant type selection
    bot.action(/^grant_type_(.+)$/, adminOnly, async (ctx) => {
        if (!ctx.session?.grantAccess) return;

        ctx.session.grantAccess.grantType = ctx.match[1];
        ctx.session.grantAccess.step = 'note';

        await ctx.answerCbQuery();
        await ctx.reply('📝 Введите заметку (или отправьте "-" чтобы пропустить):');
    });

    async function showGrantConfirmation(ctx, state) {
        const typeNames = {
            partner: '🤝 Партнёр',
            compensation: '🔧 Компенсация',
            friend: '👫 Друг',
            test: '🧪 Тест'
        };

        const message = `📋 Подтверждение выдачи доступа:\n\n` +
            `👤 Пользователь: ${state.userTelegramId}\n` +
            `📅 Дней: ${state.days}\n` +
            `📋 Тип: ${typeNames[state.grantType]}\n` +
            `📝 Заметка: ${state.note === '-' ? '—' : state.note}\n`;

        await ctx.reply(message, Markup.inlineKeyboard([
            [Markup.button.callback('✅ Подтвердить', 'confirm_grant')],
            [Markup.button.callback('❌ Отмена', 'cancel_grant')]
        ]));
    }

    bot.action('confirm_grant', adminOnly, async (ctx) => {
        const state = ctx.session?.grantAccess;
        if (!state) return ctx.answerCbQuery('Сессия истекла');

        try {
            await inviteService.grantManualAccess(ctx.from.id, {
                userTelegramId: state.userTelegramId,
                days: state.days,
                grantType: state.grantType,
                note: state.note === '-' ? null : state.note,
                deviceLimit: 3,
                nodeAccess: 'all'
            });

            delete ctx.session.grantAccess;
            await ctx.answerCbQuery('Доступ выдан!');
            await ctx.editMessageText(`✅ Доступ на ${state.days} дней выдан пользователю ${state.userTelegramId}`);
        } catch (error) {
            await ctx.answerCbQuery('Ошибка');
            await ctx.reply('Ошибка: ' + error.message);
        }
    });

    bot.action('cancel_grant', async (ctx) => {
        delete ctx.session?.grantAccess;
        await ctx.answerCbQuery('Отменено');
        await ctx.editMessageText('❌ Выдача доступа отменена.');
    });

    // /invite_rules - View and manage rules
    bot.command('invite_rules', adminOnly, async (ctx) => {
        const rules = await InviteRule.findAll();

        let message = '📋 Правила выдачи инвайтов:\n\n';

        for (const rule of rules) {
            const status = rule.is_active ? '✅' : '❌';
            message += `${status} ${rule.subscription_type}\n`;
            message += `   Инвайтов: ${rule.invites_count}\n`;
            message += `   Дней другу: ${rule.friend_days}\n`;
            message += `   Скидка: ${rule.friend_discount}%\n\n`;
        }

        const buttons = rules.map(r => [
            Markup.button.callback(`✏️ ${r.subscription_type}`, `edit_rule_${r.id}`)
        ]);

        await ctx.reply(message, Markup.inlineKeyboard(buttons));
    });

    // /invite_stats - View statistics
    bot.command('invite_stats', adminOnly, async (ctx) => {
        const args = ctx.message.text.split(' ').slice(1);
        const period = args[0] || 'week';

        const periods = {
            day: 1,
            week: 7,
            month: 30
        };

        const days = periods[period] || 7;
        const fromDate = new Date();
        fromDate.setDate(fromDate.getDate() - days);

        const { pool } = require('../config/database');

        // Get invite stats
        const inviteStats = await pool.query(`
            SELECT
                COUNT(*) FILTER (WHERE created_at >= $1) as created,
                COUNT(*) FILTER (WHERE status = 'used' AND used_at >= $1) as used,
                COUNT(*) FILTER (WHERE status = 'expired') as expired
            FROM invites
        `, [fromDate]);

        // Get conversion stats
        const conversionStats = await pool.query(`
            SELECT COUNT(DISTINCT i.used_by) as converted
            FROM invites i
            JOIN subscriptions s ON s.user_id = i.used_by AND s.is_paid = true
            WHERE i.status = 'used' AND i.used_at >= $1
        `, [fromDate]);

        // Get manual grants stats
        const grantStats = await ManualAccessGrant.getStats(fromDate, new Date());

        const stats = inviteStats.rows[0];
        const conversion = conversionStats.rows[0];

        let message = `📊 Статистика инвайтов за ${days} дней:\n\n`;
        message += `🎟 Выдано инвайтов: ${stats.created}\n`;
        message += `✅ Активировано: ${stats.used}\n`;
        message += `💰 Конверсия в оплату: ${conversion.converted}\n`;
        message += `❌ Истекло: ${stats.expired}\n\n`;

        if (grantStats.length > 0) {
            message += `📋 Ручная выдача:\n`;
            for (const stat of grantStats) {
                message += `   ${stat.grant_type}: ${stat.count} (${stat.total_days} дней)\n`;
            }
        }

        await ctx.reply(message);
    });

    // /invite_settings - View and edit settings
    bot.command('invite_settings', adminOnly, async (ctx) => {
        const settings = await InviteSetting.getAll();

        let message = '⚙️ Настройки инвайтов:\n\n';
        message += `📦 Макс. инвайтов на пользователя: ${settings.max_invites_per_user || 3}\n`;
        message += `⏰ Срок жизни инвайта: ${settings.invite_expiry_days || 90} дней\n`;
        message += `🔔 Интервал напоминаний: ${settings.reminder_interval_days || 14} дней\n`;
        message += `⚠️ Предупреждение до истечения: ${settings.expiry_warning_days || 7} дней\n`;

        await ctx.reply(message, Markup.inlineKeyboard([
            [Markup.button.callback('✏️ Изменить настройки', 'edit_invite_settings')]
        ]));
    });

    // /invite_promo - Manage promotions
    bot.command('invite_promo', adminOnly, async (ctx) => {
        const promos = await InvitePromotion.findAll();

        let message = '🎉 Акции:\n\n';

        if (promos.length === 0) {
            message += 'Нет активных акций.';
        } else {
            for (const promo of promos) {
                const status = promo.is_active ? '✅' : '❌';
                const now = new Date();
                const isRunning = promo.is_active &&
                    new Date(promo.start_date) <= now &&
                    new Date(promo.end_date) >= now;

                message += `${status} ${promo.name} ${isRunning ? '(активна)' : ''}\n`;
                message += `   Множитель: ${promo.multiplier}x\n`;
                message += `   Период: ${new Date(promo.start_date).toLocaleDateString()} - ${new Date(promo.end_date).toLocaleDateString()}\n\n`;
            }
        }

        await ctx.reply(message, Markup.inlineKeyboard([
            [Markup.button.callback('➕ Создать акцию', 'create_promo')]
        ]));
    });
}

module.exports = { setupAdminInviteHandlers };
```

**Step 2: Commit**

```bash
git add src/handlers/adminInviteHandlers.js
git commit -m "feat(handlers): add admin invite commands"
```

---

## Task 10: Cron Jobs - Automation

**Files:**
- Create: `src/cron/inviteCron.js`

**Step 1: Create cron jobs**

```javascript
// src/cron/inviteCron.js
const cron = require('node-cron');
const Invite = require('../models/invite');
const InviteSetting = require('../models/inviteSetting');
const { pool } = require('../config/database');

class InviteCron {
    constructor(bot, inviteService) {
        this.bot = bot;
        this.inviteService = inviteService;
    }

    start() {
        // Expire old invites - daily at 00:00
        cron.schedule('0 0 * * *', () => this.expireOldInvites());

        // Warn about expiring invites - daily at 10:00
        cron.schedule('0 10 * * *', () => this.warnExpiringInvites());

        // Remind about free access ending - daily at 10:00
        cron.schedule('0 10 * * *', () => this.remindExpiringFreeAccess());

        // Remind about unused invites - every day at 12:00 (filtered by interval)
        cron.schedule('0 12 * * *', () => this.remindUnusedInvites());

        // Send daily stats to admin - daily at 09:00
        cron.schedule('0 9 * * *', () => this.sendDailyStats());

        console.log('Invite cron jobs started');
    }

    async expireOldInvites() {
        try {
            const expired = await Invite.expireOld();
            console.log(`Expired ${expired.length} invites`);
        } catch (error) {
            console.error('Error expiring invites:', error);
        }
    }

    async warnExpiringInvites() {
        try {
            const warningDays = await InviteSetting.getExpiryWarningDays();
            const expiringSoon = await Invite.getExpiringSoon(warningDays);

            for (const invite of expiringSoon) {
                const owner = await pool.query(
                    'SELECT telegram_id FROM users WHERE id = $1',
                    [invite.owner_id]
                );

                if (owner.rows[0]) {
                    const daysLeft = Math.ceil(
                        (new Date(invite.expires_at) - new Date()) / (1000 * 60 * 60 * 24)
                    );

                    await this.inviteService.notifyInviteExpiringSoon(
                        owner.rows[0].telegram_id,
                        invite.code,
                        daysLeft
                    );
                }
            }
        } catch (error) {
            console.error('Error warning about expiring invites:', error);
        }
    }

    async remindExpiringFreeAccess() {
        try {
            // Find users whose free period ends in 3 days or 1 day
            const reminders = await pool.query(`
                SELECT
                    u.telegram_id,
                    s.expires_at,
                    i.friend_discount as discount
                FROM subscriptions s
                JOIN users u ON u.id = s.user_id
                LEFT JOIN invites i ON i.id = s.from_invite_id
                WHERE s.type = 'invite_free'
                AND s.expires_at::date IN (
                    CURRENT_DATE + INTERVAL '3 days',
                    CURRENT_DATE + INTERVAL '1 day'
                )
            `);

            for (const row of reminders.rows) {
                const daysLeft = Math.ceil(
                    (new Date(row.expires_at) - new Date()) / (1000 * 60 * 60 * 24)
                );

                await this.inviteService.notifyExpiringFreeAccess(
                    row.telegram_id,
                    daysLeft,
                    row.discount || 0
                );
            }
        } catch (error) {
            console.error('Error reminding about expiring free access:', error);
        }
    }

    async remindUnusedInvites() {
        try {
            const intervalDays = await InviteSetting.getReminderIntervalDays();

            // Find users with unused invites who haven't been reminded recently
            const usersToRemind = await pool.query(`
                SELECT
                    u.id,
                    u.telegram_id,
                    COUNT(i.id) as invite_count,
                    MAX(i.created_at) as last_invite_date
                FROM users u
                JOIN invites i ON i.owner_id = u.id AND i.status = 'available'
                LEFT JOIN user_notifications un ON un.user_id = u.id
                    AND un.type = 'invite_reminder'
                    AND un.sent_at > NOW() - INTERVAL '1 day' * $1
                WHERE un.id IS NULL
                GROUP BY u.id, u.telegram_id
                HAVING COUNT(i.id) > 0
            `, [intervalDays]);

            for (const user of usersToRemind.rows) {
                const message = `🎟 У вас ${user.invite_count} неиспользованных инвайтов.\n\n` +
                    `Пригласите друзей и получите бонусные дни при их оплате!\n\n` +
                    `Используйте /invites для просмотра.`;

                try {
                    await this.bot.telegram.sendMessage(user.telegram_id, message);

                    // Record reminder sent
                    await pool.query(
                        `INSERT INTO user_notifications (user_id, type, sent_at) VALUES ($1, 'invite_reminder', NOW())`,
                        [user.id]
                    );
                } catch (sendError) {
                    console.error(`Failed to send reminder to ${user.telegram_id}:`, sendError);
                }
            }
        } catch (error) {
            console.error('Error reminding about unused invites:', error);
        }
    }

    async sendDailyStats() {
        try {
            const adminIds = process.env.ADMIN_IDS?.split(',') || [];
            if (adminIds.length === 0) return;

            const yesterday = new Date();
            yesterday.setDate(yesterday.getDate() - 1);

            const stats = await pool.query(`
                SELECT
                    COUNT(*) FILTER (WHERE created_at >= $1) as created,
                    COUNT(*) FILTER (WHERE status = 'used' AND used_at >= $1) as used
                FROM invites
            `, [yesterday]);

            const grantStats = await pool.query(`
                SELECT COUNT(*) as count
                FROM manual_access_grants
                WHERE created_at >= $1
            `, [yesterday]);

            const s = stats.rows[0];
            const g = grantStats.rows[0];

            const message = `📊 Статистика инвайтов за вчера:\n\n` +
                `🎟 Выдано: ${s.created}\n` +
                `✅ Активировано: ${s.used}\n` +
                `📋 Ручная выдача: ${g.count}`;

            for (const adminId of adminIds) {
                try {
                    await this.bot.telegram.sendMessage(adminId.trim(), message);
                } catch (error) {
                    console.error(`Failed to send stats to admin ${adminId}:`, error);
                }
            }
        } catch (error) {
            console.error('Error sending daily stats:', error);
        }
    }
}

module.exports = InviteCron;
```

**Step 2: Add user_notifications table migration**

```sql
-- migrations/20260124000002_create_user_notifications.sql

CREATE TABLE IF NOT EXISTS user_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    type VARCHAR(50) NOT NULL,
    sent_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_notifications_lookup ON user_notifications(user_id, type, sent_at);
```

**Step 3: Commit**

```bash
git add src/cron/inviteCron.js migrations/20260124000002_create_user_notifications.sql
git commit -m "feat(cron): add invite automation jobs"
```

---

## Task 11: API Routes (Optional - for web panel)

**Files:**
- Create: `src/api/inviteRoutes.js`

**Step 1: Create API routes**

```javascript
// src/api/inviteRoutes.js
const express = require('express');
const router = express.Router();
const InviteRule = require('../models/inviteRule');
const InviteSetting = require('../models/inviteSetting');
const InvitePromotion = require('../models/invitePromotion');
const ManualAccessGrant = require('../models/manualAccessGrant');
const Invite = require('../models/invite');

// Middleware: require admin auth
const requireAdmin = (req, res, next) => {
    // Implement your auth check here
    if (!req.user?.isAdmin) {
        return res.status(403).json({ error: 'Forbidden' });
    }
    next();
};

// ===== Rules =====

router.get('/admin/invite-rules', requireAdmin, async (req, res) => {
    try {
        const rules = await InviteRule.findAll();
        res.json(rules);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

router.put('/admin/invite-rules/:id', requireAdmin, async (req, res) => {
    try {
        const rule = await InviteRule.update(req.params.id, req.body);
        res.json(rule);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ===== Settings =====

router.get('/admin/invite-settings', requireAdmin, async (req, res) => {
    try {
        const settings = await InviteSetting.getAll();
        res.json(settings);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

router.put('/admin/invite-settings/:key', requireAdmin, async (req, res) => {
    try {
        const setting = await InviteSetting.set(req.params.key, req.body.value);
        res.json(setting);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ===== Promotions =====

router.get('/admin/invite-promos', requireAdmin, async (req, res) => {
    try {
        const promos = await InvitePromotion.findAll();
        res.json(promos);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

router.post('/admin/invite-promos', requireAdmin, async (req, res) => {
    try {
        const promo = await InvitePromotion.create(req.body);
        res.status(201).json(promo);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

router.put('/admin/invite-promos/:id', requireAdmin, async (req, res) => {
    try {
        const promo = await InvitePromotion.update(req.params.id, req.body);
        res.json(promo);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

router.delete('/admin/invite-promos/:id', requireAdmin, async (req, res) => {
    try {
        await InvitePromotion.delete(req.params.id);
        res.status(204).send();
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ===== Manual Grants =====

router.get('/admin/manual-grants', requireAdmin, async (req, res) => {
    try {
        const { limit = 50, offset = 0 } = req.query;
        const grants = await ManualAccessGrant.findAll(parseInt(limit), parseInt(offset));
        res.json(grants);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

router.post('/admin/manual-grant', requireAdmin, async (req, res) => {
    try {
        const grant = await ManualAccessGrant.create({
            adminTelegramId: req.user.telegramId,
            ...req.body
        });
        res.status(201).json(grant);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ===== Stats =====

router.get('/admin/invite-stats', requireAdmin, async (req, res) => {
    try {
        const { from, to } = req.query;
        const fromDate = from ? new Date(from) : new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
        const toDate = to ? new Date(to) : new Date();

        const { pool } = require('../config/database');

        const stats = await pool.query(`
            SELECT
                COUNT(*) FILTER (WHERE created_at BETWEEN $1 AND $2) as created,
                COUNT(*) FILTER (WHERE status = 'used' AND used_at BETWEEN $1 AND $2) as used,
                COUNT(*) FILTER (WHERE status = 'available') as available,
                COUNT(*) FILTER (WHERE status = 'expired') as expired
            FROM invites
        `, [fromDate, toDate]);

        res.json(stats.rows[0]);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ===== User Routes =====

router.get('/user/invites', async (req, res) => {
    try {
        if (!req.user?.id) {
            return res.status(401).json({ error: 'Unauthorized' });
        }

        const invites = await Invite.findByOwner(req.user.id);
        const available = invites.filter(i => i.status === 'available').length;

        res.json({
            invites,
            stats: {
                available,
                used: invites.filter(i => i.status === 'used').length,
                expired: invites.filter(i => i.status === 'expired').length
            }
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

router.post('/invite/activate/:code', async (req, res) => {
    try {
        if (!req.user?.telegramId) {
            return res.status(401).json({ error: 'Unauthorized' });
        }

        // This would typically call inviteService.activateInvite
        res.json({ message: 'Use Telegram bot to activate invites' });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

module.exports = router;
```

**Step 2: Commit**

```bash
git add src/api/inviteRoutes.js
git commit -m "feat(api): add invite management API routes"
```

---

## Task 12: Integration with Payment Handler

**Files:**
- Modify: `src/handlers/paymentHandler.js` (add invite grant call)

**Step 1: Add invite grant to payment success handler**

In existing payment handler, after successful payment processing, add:

```javascript
// In paymentHandler.js, after successful payment:

// ... existing payment success code ...

// Grant invites if applicable
try {
    const result = await inviteService.grantInvites(
        user.id,
        user.telegram_id,
        subscription.type // e.g., '12_months'
    );

    if (result.granted > 0) {
        console.log(`Granted ${result.granted} invites to user ${user.id}`);
    }
} catch (error) {
    console.error('Error granting invites:', error);
    // Don't fail payment if invite grant fails
}
```

**Step 2: Commit**

```bash
git add src/handlers/paymentHandler.js
git commit -m "feat(payment): integrate invite grants on successful payment"
```

---

## Task 13: Initialization and Wiring

**Files:**
- Create/Modify: `src/app.js` or main entry point

**Step 1: Wire everything together**

```javascript
// In src/app.js or main entry point

const { Telegraf } = require('telegraf');
const session = require('telegraf/session');
const InviteService = require('./services/inviteService');
const InviteCron = require('./cron/inviteCron');
const { setupInviteHandlers } = require('./handlers/inviteHandlers');
const { setupAdminInviteHandlers } = require('./handlers/adminInviteHandlers');
const inviteRoutes = require('./api/inviteRoutes');

// ... existing bot setup ...

// Session for admin conversations
bot.use(session());

// Initialize invite service
const inviteService = new InviteService(bot, userService, subscriptionService);

// Setup invite handlers
setupInviteHandlers(bot, inviteService, userService);
setupAdminInviteHandlers(bot, inviteService, isAdmin);

// Start cron jobs
const inviteCron = new InviteCron(bot, inviteService);
inviteCron.start();

// Add API routes (if using Express)
app.use('/api', inviteRoutes);

// ... rest of app ...
```

**Step 2: Commit**

```bash
git add src/app.js
git commit -m "feat: wire invite system into application"
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Database migration | `migrations/20260124000001_create_invite_tables.sql` |
| 2 | Invite model | `src/models/invite.js` |
| 3 | InviteRule model | `src/models/inviteRule.js` |
| 4 | InviteSetting model | `src/models/inviteSetting.js` |
| 5 | InvitePromotion model | `src/models/invitePromotion.js` |
| 6 | ManualAccessGrant model | `src/models/manualAccessGrant.js` |
| 7 | InviteService | `src/services/inviteService.js` |
| 8 | User bot handlers | `src/handlers/inviteHandlers.js` |
| 9 | Admin bot handlers | `src/handlers/adminInviteHandlers.js` |
| 10 | Cron jobs | `src/cron/inviteCron.js` |
| 11 | API routes | `src/api/inviteRoutes.js` |
| 12 | Payment integration | `src/handlers/paymentHandler.js` (modify) |
| 13 | App wiring | `src/app.js` (modify) |

**Total commits:** 13
**Estimated implementation:** Execute tasks sequentially, committing after each
