/**
 * ReliBank Selenium Large Transfer and Support Script
 * This script tests the scenario where a user:
 * 1. Logs in
 * 2. Transfers more money than available in their account (ReliBank allows overdrafts)
 * 3. Navigates to support
 * 4. Submits a question about their account balance
 *
 * Documentation: https://docs.newrelic.com/docs/synthetics/new-relic-synthetics/scripting-monitors/writing-scripted-browsers
 */

var assert = require('assert');

// Main async function
(async function() {
  try {
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

    // Wait for the Transfer Funds card to load
    await $browser.wait($driver.until.elementLocated($driver.By.css('input[type="number"]')), 5000);
    console.log('Transfer form loaded');

    // Find and enter transfer amount (more than checking account balance of $8,500.25)
    const amountField = await $browser.findElement($driver.By.css('input[type="number"]'));
    console.log('Found amount field');

    await amountField.sendKeys('10000');
    console.log('Entered transfer amount: $10,000 (exceeds checking balance of $8,500.25)');

    // Find the "From" dropdown
    const fromSelect = await $browser.findElement($driver.By.id('transfer-from-account-select'));
    console.log('Found from account dropdown');

    // Click to open dropdown and select checking
    await fromSelect.click();
    console.log('Opened from account dropdown');

    // Wait a moment for dropdown to open
    await $browser.sleep(500);

    // Find and click "checking" option in the dropdown
    const checkingOption = await $browser.findElement($driver.By.css('li[data-value="checking"]'));
    await checkingOption.click();
    console.log('Selected checking as from account');

    // Find the "To" dropdown
    const toSelect = await $browser.findElement($driver.By.id('transfer-to-account-select'));
    console.log('Found to account dropdown');

    // Click to open dropdown
    await toSelect.click();
    console.log('Opened to account dropdown');

    // Wait a moment for dropdown to open
    await $browser.sleep(500);

    // Find and click "savings" option
    const savingsOption = await $browser.findElement($driver.By.css('li[data-value="savings"]'));
    await savingsOption.click();
    console.log('Selected savings as to account');

    // Find and click the Complete Transfer button
    const transferButton = await $browser.findElement($driver.By.css('button[type="submit"]'));
    console.log('Found Complete Transfer button');

    await transferButton.click();
    console.log('Clicked Complete Transfer button');

    // Wait for success/error message to appear
    await $browser.wait($driver.until.elementLocated($driver.By.css('.MuiAlert-message')), 5000);
    console.log('Transfer completed - message appeared');

    // Verify a message was displayed (ReliBank allows overdrafts, so this will succeed)
    const alertMessage = await $browser.findElement($driver.By.css('.MuiAlert-message'));
    const text = await alertMessage.getText();
    assert.ok(text.length > 0, 'Alert message should be displayed');
    console.log('Transfer processed! Message: ' + text);

    // Give New Relic time to capture the transaction
    console.log('Waiting 3 seconds for New Relic to capture transaction telemetry...');
    await $browser.sleep(3000);

    // Now navigate to Support
    console.log('Navigating to Support page to submit a question');

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

    // Type the support question
    const supportMessage = 'I just transferred $10,000 from checking to savings. Can you help me understand my new account balance?';
    await messageField.sendKeys(supportMessage);
    console.log('Typed support message: ' + supportMessage);

    // Find and click the Send button
    const sendButton = await $browser.findElement($driver.By.xpath('//button[contains(text(), "Send")]'));
    console.log('Found Send button');

    await sendButton.click();
    console.log('Clicked Send button - support message submitted');

    // Wait a moment for the message to be sent
    await $browser.sleep(1000);

    console.log('Support scenario completed successfully!');
    console.log('Summary: Login -> Large transfer ($10k overdraft) -> Support question submitted');

    // Final wait to ensure all telemetry is sent to New Relic
    console.log('Final wait of 2 seconds for telemetry to be sent...');
    await $browser.sleep(2000);
    console.log('Script completed!');

  } catch (error) {
    console.error('Script failed with error:', error);
    throw error;
  }
})();
