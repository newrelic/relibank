/**
 * ReliBank Selenium Specialist Chatbot Script
 * This script simulates a user journey that:
 * 1. Navigates directly to support page
 * 2. Asks a specialist question (triggers 8-second delay)
 * 3. Waits for response
 * 4. Stays on page for 5 seconds for session replay capture
 *
 * Documentation: https://docs.newrelic.com/docs/synthetics/new-relic-synthetics/scripting-monitors/writing-scripted-browsers
 */

var assert = require('assert');

// Specialist questions that trigger delegation
const SPECIALIST_QUESTIONS = [
  "I'd like to ask a specialist about my spending patterns this month.",
  "Please connect me with a specialist to analyze my account balances.",
  "Can you connect me with a specialist? I need help understanding my transactions.",
  "I'd like to speak with a specialist about my financial health.",
  "Please connect me with a specialist to review my savings strategy.",
  "I need a specialist to help me analyze my top spending categories.",
  "Can a specialist help me understand where my money is going?",
  "I'd like to ask a specialist for a detailed breakdown of my expenses.",
  "Please connect me with a specialist to discuss my budget optimization.",
  "I need to speak with a specialist about unusual transactions in my account.",
  "Can you connect me with a specialist to review my payment patterns?",
  "I'd like a specialist to analyze my spending vs income ratio.",
  "Please connect me with a specialist for a comprehensive financial review.",
  "I need a specialist to help me identify areas where I can save money.",
  "Can you connect me with a specialist to discuss my account activity trends?",
  "I'd like to ask a specialist about improving my financial planning.",
  "Please connect me with a specialist to analyze my transaction history.",
  "I need a specialist to provide insights on my account management.",
  "Can a specialist help me with a detailed financial analysis?",
  "I'd like to speak with a specialist about optimizing my spending habits."
];

// Main async function
(async function() {
  try {
    // Select a random specialist question
    const randomQuestion = SPECIALIST_QUESTIONS[Math.floor(Math.random() * SPECIALIST_QUESTIONS.length)];
    console.log('Selected specialist question: ' + randomQuestion);

    // Navigate directly to ReliBank support page
    await $browser.get('http://relibank.westus2.cloudapp.azure.com/support');
    console.log('Navigated directly to ReliBank support page');

    // Wait for support page to load
    await $browser.wait($driver.until.urlContains('support'), 10000);
    console.log('Support page loaded successfully');

    // Wait for the chat input field to load
    await $browser.wait($driver.until.elementLocated($driver.By.css('input[type="text"]')), 5000);
    console.log('Support chat loaded');

    // Find the message input field
    const messageField = await $browser.findElement($driver.By.css('input[type="text"]'));
    console.log('Found message input field');

    // Type the specialist question
    await messageField.sendKeys(randomQuestion);
    console.log('Typed specialist question: ' + randomQuestion);

    // Find and click the Send button
    const sendButton = await $browser.findElement($driver.By.xpath('//button[contains(text(), "Send")]'));
    console.log('Found Send button');

    await sendButton.click();
    console.log('Clicked Send button - specialist question submitted');

    // Wait for chatbot to start responding (specialist delegation takes ~8 seconds)
    console.log('Waiting for chatbot specialist response (may take 8+ seconds)...');
    await $browser.sleep(3000);

    // Look for the chatbot response messages
    try {
      // Wait for any message to appear in the chat
      await $browser.wait(
        $driver.until.elementLocated($driver.By.css('.message, .chat-message, [class*="message"]')),
        15000
      );
      console.log('Chatbot response detected');
    } catch (e) {
      console.log('Note: Could not detect chatbot response element, continuing...');
    }

    // Stay on the page for 5 seconds to ensure session replay captures the interaction
    console.log('Staying on support page for 5 seconds for session replay capture...');
    await $browser.sleep(5000);

    console.log('Specialist chatbot scenario completed successfully!');
    console.log('Summary: Support -> Specialist Question -> Wait for Response');

    // Logout to properly close the session
    console.log('Logging out to close session...');
    try {
      // Find and click the logout button (adjust selector based on your app)
      const logoutButton = await $browser.findElement($driver.By.css('button[aria-label="Logout"], button:contains("Logout"), a[href*="logout"]'));
      await logoutButton.click();
      console.log('Clicked logout button');
      await $browser.sleep(1000);
    } catch (e) {
      console.log('Logout button not found or logout failed, closing session via navigation');
      // Alternative: navigate away to end session
      await $browser.get('about:blank');
    }

    // Final wait to ensure all telemetry is sent to New Relic
    console.log('Final wait of 2 seconds for telemetry to be sent...');
    await $browser.sleep(2000);
    console.log('Script completed! Session closed.');

  } catch (error) {
    console.error('Script failed with error:', error);
    throw error;
  }
})();
