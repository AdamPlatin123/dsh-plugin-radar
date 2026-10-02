#!/usr/bin/env node
/* fetch-cui.mjs — 崔佬推荐抓取器：X @tianyicui 时间线 → 插件推荐过滤 → cui-picks.json
 * 链路：代理(127.0.0.1:10811) → 首页取 ct0 → x-client-transaction-id 反爬 → GraphQL
 * 用法：node fetch-cui.mjs [--days 30] [--out out/cui-picks.json]
 */
import { setGlobalDispatcher, ProxyAgent, fetch as ufetch } from 'undici';
import { ClientTransaction, fetchXDocument } from 'x-client-transaction-id';
import { writeFileSync, mkdirSync } from 'node:fs';

if (process.env.CUI_PROXY) setGlobalDispatcher(new ProxyAgent(process.env.CUI_PROXY));

const AUTH = process.env.X_AUTH_TOKEN;
const BEARER = 'AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA';
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36';
const SCREEN = 'tianyicui';
const args = process.argv.slice(2);
const days = Number(args[args.indexOf('--days') + 1] || 30);
const out = args[args.indexOf('--out') + 1] || 'out/cui-picks.json';

const gqlFeatureUser = { hidden_profile_subscriptions_enabled: true, rweb_tipjar_consumption_enabled: true, responsive_web_graphql_exclude_directive_enabled: true, verified_phone_label_enabled: false, subscriptions_verification_info_is_identity_verified_enabled: true, subscriptions_verification_info_verified_since_enabled: true, highlights_tweets_tab_ui_enabled: true, responsive_web_twitter_article_notes_tab_enabled: true, subscriptions_feature_can_gift_premium: true, creator_subscriptions_tweet_preview_api_enabled: true, responsive_web_graphql_skip_user_profile_image_extensions_enabled: false, responsive_web_graphql_timeline_navigation_enabled: true };
const gqlFeatureFeed = { rweb_tipjar_consumption_enabled: true, responsive_web_graphql_exclude_directive_enabled: true, verified_phone_label_enabled: false, creator_subscriptions_tweet_preview_api_enabled: true, responsive_web_graphql_timeline_navigation_enabled: true, responsive_web_graphql_skip_user_profile_image_extensions_enabled: false, communities_web_enable_tweet_community_results_fetch: true, c9s_tweet_anatomy_moderator_badge_enabled: true, articles_preview_enabled: true, responsive_web_edit_tweet_api_enabled: true, graphql_is_translatable_rweb_tweet_is_translatable_enabled: true, view_counts_everywhere_api_enabled: true, longform_notetweets_consumption_enabled: true, responsive_web_twitter_article_tweet_consumption_enabled: true, tweet_awards_web_tipping_enabled: false, creator_subscriptions_quote_tweet_preview_enabled: false, freedom_of_speech_not_reach_fetch_enabled: true, standardized_nudges_misinfo: true, tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled: true, rweb_video_timestamps_enabled: true, longform_notetweets_rich_text_read_enabled: true, longform_notetweets_inline_media_enabled: true, responsive_web_enhance_cards_enabled: false };

async function liveIds() {
  try {
    const r = await ufetch('https://cdn.jsdelivr.net/gh/fa0311/TwitterInternalAPIDocument@master/docs/json/API.json');
    const d = await r.json();
    return { UserByScreenName: d.graphql.UserByScreenName.queryId, UserTweets: d.graphql.UserTweets.queryId };
  } catch { return null; }
}
const ids = (await liveIds()) || { UserByScreenName: 'Gb-d6r0vxPOADdG62OEBpQ', UserTweets: 'eoJ5zbv51Z_KVl81v9PmLQ' };

// ① ct0
const home = await ufetch('https://x.com/', { headers: { 'user-agent': UA, cookie: `auth_token=${AUTH}` } });
const setCK = home.headers.getSetCookie?.() || [];
const jar = new Map([['auth_token', AUTH]]);
for (const c of setCK) { const [kv] = c.split(';'); const i = kv.indexOf('='); jar.set(kv.slice(0, i), kv.slice(i + 1)); }
const ct0 = jar.get('ct0');
if (!ct0) throw new Error('ct0 未下发（auth_token 失效或被挑战）');
const COOKIE = [...jar].map(([k, v]) => k + '=' + v).join('; ');
console.error(`[cui] ct0 OK (${ct0.length})，罐 ${jar.size} 键`);

// ② 反爬 ID
const doc = await fetchXDocument();
const tx = await ClientTransaction.create(doc);
const gqlHeaders = async (path) => ({
  authorization: `Bearer ${BEARER}`,
  cookie: COOKIE,
  'x-csrf-token': ct0,
  'x-twitter-auth-type': 'OAuth2Session',
  'x-twitter-active-user': 'yes',
  'x-twitter-client-language': 'en',
  'x-client-transaction-id': await tx.generateTransactionId('GET', path),
  'user-agent': UA,
  referer: 'https://x.com/',
});

// ③ UserByScreenName
const p1 = `/i/api/graphql/${ids.UserByScreenName}/UserByScreenName`;
const u1 = `https://x.com${p1}?` + new URLSearchParams({ variables: JSON.stringify({ screen_name: SCREEN }), features: JSON.stringify(gqlFeatureUser) });
const r1 = await ufetch(u1, { headers: await gqlHeaders(p1) });
const d1 = await r1.json();
const user = d1?.data?.user?.result;
if (!user?.rest_id) throw new Error(`UserByScreenName 失败 HTTP${r1.status}: ` + JSON.stringify(d1).slice(0, 200));
console.error(`[cui] user ${user.legacy.name} (@${SCREEN}) rest_id=${user.rest_id}`);

// ④ UserTweets
const p2 = `/i/api/graphql/${ids.UserTweets}/UserTweets`;
const u2 = `https://x.com${p2}?` + new URLSearchParams({
  variables: JSON.stringify({ userId: user.rest_id, count: 100, includePromotedContent: false, withQuickPromoteEligibilityTweetFields: false, withVoice: true }),
  features: JSON.stringify(gqlFeatureFeed),
});
const r2 = await ufetch(u2, { headers: await gqlHeaders(p2) });
const d2 = await r2.json();
const entries = d2?.data?.user?.result?.timeline_v2?.timeline?.instructions?.flatMap(i => i.entries || i.entry ? (i.entries || [i.entry]) : []) || [];
console.error(`[cui] 原始条目 ${entries.length}`);

// ⑤ 解析 + 过滤
const KW = /(dsh|DSH|插件|plugin|推荐|Claude\s*Code|DeepSeek|harness|Harness|MCP|mcp)/;
const cutoff = Date.now() - days * 86400e3;
const tweets = [];
for (const e of entries) {
  const t = e?.content?.itemContent?.tweet_results?.result?.legacy;
  if (!t) continue;
  if (t.in_reply_to_status_id_str) continue;         // 跳过回复
  const ts = new Date(t.created_at).getTime();
  if (ts < cutoff) continue;
  const text = t.full_text.replace(/https:\/\/t\.co\/\S+/g, '').trim();
  if (!text || !KW.test(text)) continue;
  tweets.push({
    id: t.id_str,
    date: t.created_at,
    text,
    url: `https://x.com/${SCREEN}/status/${t.id_str}`,
    stars: (t.favorite_count || 0),
    media: (t.extended_entities?.media || []).map(m => m.media_url_https).slice(0, 2),
  });
}
tweets.sort((a, b) => new Date(b.date) - new Date(a.date));
const doc_out = { updated: new Date().toISOString().slice(0, 10), source: `@${SCREEN}`, days, count: tweets.length, tweets: tweets.slice(0, 60) };
mkdirSync(out.split('/').slice(0, -1).join('/') || '.', { recursive: true });
writeFileSync(out, JSON.stringify(doc_out, null, 1) + '\n');
console.error(`[cui] 命中 ${tweets.length} 条 → ${out}`);
