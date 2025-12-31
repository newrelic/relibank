/**
 * ReliBank Selenium Spending Analysis Support Script
 * This script tests a normal user flow followed by a spending analysis request:
 * 1. Logs in
 * 2. Performs a normal transfer (desktop only - skipped on mobile due to UI differences)
 * 3. Navigates to Support
 * 4. Asks a normal question and waits for response
 * 5. Asks to "Analyze my spending" (triggers blocking JS demo)
 * 6. Rage clicks during UI freeze
 *
 * Documentation: https://docs.newrelic.com/docs/synthetics/new-relic-synthetics/scripting-monitors/writing-scripted-browsers
 */

var assert = require('assert');

// Main async function
(async function() {
  try {
    // Generate a random transfer amount between $10 and $50
    const transferAmount = Math.floor(Math.random() * 41) + 10;
    console.log('Generated random transfer amount: $' + transferAmount);

    // Navigate to ReliBank login page
    await $browser.get('http://relibank.westus2.cloudapp.azure.com/');
    console.log('Navigated to ReliBank homepage');

    // Wait for the login page to load and find the Sign In button
    const submitButton = await $browser.findElement($driver.By.css('button[type="submit"]'));
    console.log('Found submit button on login page');

    // Click Sign In button without entering credentials (form has default values)
    await submitButton.click();
    console.log('Clicked Sign In button');

    // Wait for navigation to complete and verify we're logged in
    await $browser.wait($driver.until.urlContains('dashboard'), 10000);
    console.log('Successfully logged in - redirected to dashboard');

    // Verify we're on the dashboard
    const url = await $browser.getCurrentUrl();
    assert.ok(url.includes('dashboard'), 'Should be on dashboard page after login');
    console.log('Login successful! Current URL: ' + url);

    // Try to perform a transfer
    try {
      // Wait for the Transfer Funds card to load
      await $browser.wait($driver.until.elementLocated($driver.By.css('input[type="number"]')), 5000);
      console.log('Transfer form loaded');

    // Find and enter transfer amount
    const amountField = await $browser.findElement($driver.By.css('input[type="number"]'));
    console.log('Found amount field');

    await amountField.sendKeys(transferAmount.toString());
    console.log('Entered transfer amount: $' + transferAmount);

    // Find the "From" dropdown
    const fromSelect = await $browser.findElement($driver.By.id('from-account-select'));
    console.log('Found from account dropdown');

    // Click to open dropdown and select checking
    await fromSelect.click();
    console.log('Opened from account dropdown');

    // Wait for dropdown menu to appear in the portal and select checking
    await $browser.sleep(800);
    const checkingOption = await $browser.findElement($driver.By.xpath('//li[@role="option" and contains(., "Checking")]'));
    await checkingOption.click();
    console.log('Selected checking as from account');

    // Wait for the first dropdown to close completely before opening the second one
    await $browser.sleep(1000);

    // Find the "To" dropdown
    const toSelect = await $browser.findElement($driver.By.id('to-account-select'));
    console.log('Found to account dropdown');

    // Click to open dropdown
    await toSelect.click();
    console.log('Opened to account dropdown');

    // Wait for dropdown menu to appear in the portal and select savings
    await $browser.sleep(800);
    const savingsOption = await $browser.findElement($driver.By.xpath('//li[@role="option" and contains(., "Savings")]'));
    await savingsOption.click();
    console.log('Selected savings as to account');

    // Wait for dropdown menu to close before clicking submit
    await $browser.sleep(1000);
    console.log('Dropdown closed, ready to submit');

    // Find and click the Complete Transfer button
    const transferButton = await $browser.findElement($driver.By.css('button[type="submit"]'));
    console.log('Found Complete Transfer button');

    await transferButton.click();
    console.log('Clicked Complete Transfer button');

    // Wait for success message to appear
    await $browser.wait($driver.until.elementLocated($driver.By.css('.MuiAlert-message')), 5000);
    console.log('Transfer completed - success message appeared');

      // Verify the success message
      const alertMessage = await $browser.findElement($driver.By.css('.MuiAlert-message'));
      const text = await alertMessage.getText();
      assert.ok(text.includes('Successfully transferred'), 'Success message should confirm transfer');
      console.log('Transfer successful! Message: ' + text);
    } catch (transferError) {
      console.log('Transfer step skipped (mobile device or UI not available): ' + transferError.message);
    }

    // Now navigate to Support
    console.log('Navigating to Support page for chatbot interaction');

    const supportLink = await $browser.findElement($driver.By.css('a[href="/support"]'));
    await supportLink.click();
    console.log('Clicked Support link');

    // Wait for support page to load
    await $browser.wait($driver.until.urlContains('support'), 5000);
    console.log('Successfully navigated to support page');

    // Wait for the chat input field to load
    await $browser.wait($driver.until.elementLocated($driver.By.css('input[type="text"]')), 5000);
    console.log('Support chat loaded');

    // Find the message input field
    const messageField = await $browser.findElement($driver.By.css('input[type="text"]'));
    console.log('Found message input field');

    // Type a normal question first
    const normalQuestion = 'What are my current account balances?';
    await messageField.sendKeys(normalQuestion);
    console.log('Typed normal question: ' + normalQuestion);

    // Find and click the Send button
    const sendButton1 = await $browser.findElement($driver.By.xpath('//button[contains(text(), "Send")]'));
    console.log('Found Send button');

    await sendButton1.click();
    console.log('Clicked Send button - normal question submitted');

    // Wait for the chatbot to respond (give it time to process)
    console.log('Waiting for chatbot response...');
    await $browser.sleep(4000);

    // Now ask the spending analysis question that triggers the blocking JS
    console.log('Preparing to ask spending analysis question (will trigger blocking JS)');

    // Find the message input field again
    const messageField2 = await $browser.findElement($driver.By.css('input[type="text"]'));
    console.log('Found message input field for second question');

    // Type the spending analysis question
    const spendingQuestion = 'Analyze my spending';
    await messageField2.sendKeys(spendingQuestion);
    console.log('Typed spending analysis question: ' + spendingQuestion);

    // Find and click the Send button
    const sendButton2 = await $browser.findElement($driver.By.xpath('//button[contains(text(), "Send")]'));
    console.log('Found Send button for spending analysis question');

    await sendButton2.click();
    console.log('Clicked Send button - spending analysis question submitted');
    console.log('NOTE: This will trigger blocking Fibonacci calculation (fib(42)) causing UI freeze');

    // Simulate frustrated user rage-clicking the Send button while page is frozen
    console.log('Simulating frustrated user rage-clicking Send button during UI freeze...');

    // Small initial delay before rage clicking starts
    await $browser.sleep(500);

    // Rage click the Send button multiple times with short intervals
    for (let i = 0; i < 6; i++) {
      await $browser.sleep(300); // Short delay between clicks
      try {
        const rageClickButton = await $browser.findElement($driver.By.xpath('//button[contains(text(), "Send")]'));
        await rageClickButton.click();
        console.log('Rage click ' + (i + 1) + ' - attempting click');
      } catch (e) {
        // Button might not be clickable during freeze, that's expected
        console.log('Rage click ' + (i + 1) + ' - click failed (expected during UI freeze)');
      }
    }

    // Wait for the blocking operation to complete and chatbot response
    console.log('Waiting for blocking calculation to complete and chatbot response...');
    await $browser.sleep(4000);

    console.log('Spending analysis scenario completed successfully!');
    console.log('Summary: Login -> Transfer -> Support -> Normal question -> Spending analysis (blocking JS)');

    // Final wait to ensure all telemetry is sent to New Relic
    console.log('Final wait for telemetry to be sent...');
    await $browser.sleep(2000);
    console.log('Script completed!');

  } catch (error) {
    console.error('Script failed with error:', error);
    throw error;
  }
})();
