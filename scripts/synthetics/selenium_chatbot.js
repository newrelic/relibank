/**
 * ReliBank Selenium Insufficient Funds and Support Script
 * This script tests the scenario where a user:
 * 1. Logs in
 * 2. Attempts to transfer more money than available in their account
 * 3. Receives an insufficient funds error
 * 4. Navigates to support
 * 5. Submits a question about why the transfer didn't go through
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

    // Wait for error message to appear
    await $browser.wait($driver.until.elementLocated($driver.By.css('.MuiAlert-message')), 5000);
    console.log('Transfer failed - error message appeared');

    // Give New Relic time to capture the error
    console.log('Waiting 3 seconds for New Relic to capture error telemetry...');
    await $browser.sleep(3000);

    // Verify the error message
    const alertMessage = await $browser.findElement($driver.By.css('.MuiAlert-message'));
    const text = await alertMessage.getText();
    assert.ok(text.includes('Insufficient funds'), 'Error message should indicate insufficient funds');
    console.log('Transfer failed as expected! Message: ' + text);

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
    const supportMessage = 'Why did my transfer not go through? I tried to transfer $10,000 from checking to savings but got an error.';
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
    console.log('Summary: Login -> Insufficient funds transfer -> Support question submitted');

    // Final wait to ensure all telemetry is sent to New Relic
    console.log('Final wait of 2 seconds for telemetry to be sent...');
    await $browser.sleep(2000);
    console.log('Script completed!');

  } catch (error) {
    console.error('Script failed with error:', error);
    throw error;
  }
})();
