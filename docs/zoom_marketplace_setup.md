# Zoom Marketplace Setup Guide

This document outlines the required configuration for setting up the Zoom integration on the Zoom App Marketplace. 
The platform uses the **Authorization Code OAuth** flow (User-managed OAuth app) so each recruiter can authenticate their own Zoom account to schedule interviews.

## 1. App Creation

1. Go to the [Zoom App Marketplace](https://marketplace.zoom.us/).
2. Click **Develop** -> **Build App** (or Build Video SDK, Server-to-Server, etc.).
3. Choose **OAuth** (User-managed app). Do NOT choose Server-to-Server OAuth for this application.
4. Give your app a name, select **User-managed app**, and ensure it is not published to the Zoom App Marketplace unless you intend to offer it publicly. (If internal only, leave it unpublished but ensure recruiters are on the same account, or publish it as a private/unlisted app).

## 2. App Credentials

Note down your `Client ID` and `Client Secret`. These must be set in the backend `.env` file as:
- `ZOOM_CLIENT_ID`
- `ZOOM_CLIENT_SECRET`

## 3. Redirect URLs

Under the **OAuth Information** section, set the following:
- **Redirect URL for OAuth**: `https://<YOUR_BACKEND_DOMAIN>/api/zoom/oauth/callback`
- **OAuth Allow List**: `https://<YOUR_BACKEND_DOMAIN>/api/zoom/oauth/callback`

(Replace `<YOUR_BACKEND_DOMAIN>` with your actual production backend URL, matching the `BACKEND_URL` in your `.env`.)

## 4. Scopes

The application requires the following scopes to function correctly:

- `meeting:write` (Allows the app to schedule and delete meetings on behalf of the user)
- `meeting:read` (Allows the app to read meeting details)
- `user:read` (Allows the app to fetch the user's `zoom_user_id` and `zoom_email` during the OAuth callback)

## 5. Feature: Event Subscriptions (Webhooks)

The application relies on webhooks to know when a meeting has started and ended to automatically start and stop the AI analysis.

1. Toggle **Event Subscriptions** to ON.
2. Click **Add Event Subscription**.
3. **Subscription Name**: `Interview AI Events`
4. **Event Notification Endpoint URL**: `https://<YOUR_BACKEND_DOMAIN>/api/zoom`
5. **Add Events**:
   - Meeting -> `Meeting has been started` (`meeting.started`)
   - Meeting -> `Meeting has been ended` (`meeting.ended`)

Note the **Secret Token** generated for the webhook. Set this in the backend `.env` as:
- `ZOOM_WEBHOOK_SECRET`

## 6. Migration and Coexistence

If migrating from an old Server-to-Server app:
1. Do not immediately delete the old Server-to-Server app. Keep its webhooks active so existing scheduled meetings are processed correctly.
2. New meetings will be scheduled using the new OAuth app. The webhook endpoint will receive events from both apps. 
3. The platform natively deduplicates webhook events based on `meeting_id`, so it is completely safe if both apps send a webhook for the same meeting.
