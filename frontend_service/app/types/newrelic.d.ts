/**
 * TypeScript definitions for New Relic Browser Agent
 * These types enable type-safe usage of the New Relic Browser API
 */

interface NewRelicBrowserAgent {
  /**
   * Sets the user ID for the current browser session.
   * This associates all subsequent page views and actions with the specified user.
   *
   * @param userId - The unique identifier for the user
   */
  setUserId(userId: string): void;

  /**
   * Sets a custom attribute that will be attached to all events.
   *
   * @param name - The name of the attribute
   * @param value - The value of the attribute (string, number, or boolean)
   */
  setCustomAttribute(name: string, value: string | number | boolean): void;

  /**
   * Records a custom page action event.
   *
   * @param name - The name of the page action
   * @param attributes - Optional attributes to attach to the event
   */
  addPageAction(name: string, attributes?: Record<string, any>): void;

  /**
   * Notifies New Relic of an error.
   *
   * @param error - The error object or message
   * @param customAttributes - Optional custom attributes
   */
  noticeError(error: Error | string, customAttributes?: Record<string, any>): void;
}

interface Window {
  /**
   * New Relic Browser Agent global object
   */
  newrelic?: NewRelicBrowserAgent;
}

declare const newrelic: NewRelicBrowserAgent | undefined;
