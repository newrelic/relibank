/**
 * ReliBank Selenium Login and Transfer Script
 * This script opens the ReliBank application, logs in, and performs a funds transfer
 *
 * Documentation: https://docs.newrelic.com/docs/synthetics/new-relic-synthetics/scripting-monitors/writing-scripted-browsers
 */

var assert = require('assert');

// Navigate to ReliBank login page
$browser.get('http://relibank.westus2.cloudapp.azure.com/').then(function(){
  console.log('Navigated to ReliBank homepage');

  // Wait for the login page to load and find the Sign In button
  return $browser.findElement($driver.By.css('button[type="submit"]')).then(function(submitButton){
    console.log('Found submit button on login page');

    // Click Sign In button without entering credentials (form has default values)
    return submitButton.click().then(function(){
      console.log('Clicked Sign In button');

      // Wait for navigation to complete and verify we're logged in
      return $browser.wait($driver.until.urlContains('dashboard'), 10000).then(function(){
        console.log('Successfully logged in - redirected to dashboard');

        // Verify we're on the dashboard
        return $browser.getCurrentUrl().then(function(url){
          assert.ok(url.includes('dashboard'), 'Should be on dashboard page after login');
          console.log('Login successful! Current URL: ' + url);

          // Wait for the Transfer Funds card to load
          return $browser.wait($driver.until.elementLocated($driver.By.css('input[type="number"]')), 5000).then(function(){
            console.log('Transfer form loaded');

            // Find and enter transfer amount
            return $browser.findElement($driver.By.css('input[type="number"]')).then(function(amountField){
              console.log('Found amount field');

              return amountField.sendKeys('100').then(function(){
                console.log('Entered transfer amount: $100');

                // Find the "From" dropdown (first select element)
                return $browser.findElement($driver.By.id('from-account-select')).then(function(fromSelect){
                  console.log('Found from account dropdown');

                  // Click to open dropdown and select checking
                  return fromSelect.click().then(function(){
                    console.log('Opened from account dropdown');

                    // Wait a moment for dropdown to open
                    return $browser.sleep(500).then(function(){

                      // Find and click "checking" option in the dropdown
                      return $browser.findElement($driver.By.css('li[data-value="checking"]')).then(function(checkingOption){
                        return checkingOption.click().then(function(){
                          console.log('Selected checking as from account');

                          // Find the "To" dropdown
                          return $browser.findElement($driver.By.id('to-account-select')).then(function(toSelect){
                            console.log('Found to account dropdown');

                            // Click to open dropdown
                            return toSelect.click().then(function(){
                              console.log('Opened to account dropdown');

                              // Wait a moment for dropdown to open
                              return $browser.sleep(500).then(function(){

                                // Find and click "savings" option
                                return $browser.findElement($driver.By.css('li[data-value="savings"]')).then(function(savingsOption){
                                  return savingsOption.click().then(function(){
                                    console.log('Selected savings as to account');

                                    // Find and click the Complete Transfer button
                                    return $browser.findElement($driver.By.css('button[type="submit"]')).then(function(transferButton){
                                      console.log('Found Complete Transfer button');

                                      return transferButton.click().then(function(){
                                        console.log('Clicked Complete Transfer button');

                                        // Wait for success message to appear
                                        return $browser.wait($driver.until.elementLocated($driver.By.css('.MuiAlert-message')), 5000).then(function(){
                                          console.log('Transfer completed - success message appeared');

                                          // Verify the success message
                                          return $browser.findElement($driver.By.css('.MuiAlert-message')).then(function(alertMessage){
                                            return alertMessage.getText().then(function(text){
                                              assert.ok(text.includes('Successfully transferred'), 'Success message should confirm transfer');
                                              console.log('Transfer successful! Message: ' + text);

                                              // Wait a moment before clicking other buttons
                                              return $browser.sleep(1000).then(function(){

                                                // Click the "Show All" button in transactions if it exists
                                                return $browser.findElements($driver.By.xpath("//button[contains(text(), 'Show All')]")).then(function(showAllButtons){
                                                  if (showAllButtons.length > 0) {
                                                    console.log('Found Show All transactions button');
                                                    return showAllButtons[0].click().then(function(){
                                                      console.log('Clicked Show All transactions button');
                                                      return $browser.sleep(500);
                                                    });
                                                  } else {
                                                    console.log('Show All button not found, skipping');
                                                    return Promise.resolve();
                                                  }
                                                }).then(function(){

                                                  // Click the "Show Less" button if it exists
                                                  return $browser.findElements($driver.By.xpath("//button[contains(text(), 'Show Less')]")).then(function(showLessButtons){
                                                    if (showLessButtons.length > 0) {
                                                      console.log('Found Show Less transactions button');
                                                      return showLessButtons[0].click().then(function(){
                                                        console.log('Clicked Show Less transactions button');
                                                        return $browser.sleep(500);
                                                      });
                                                    } else {
                                                      console.log('Show Less button not found, skipping');
                                                      return Promise.resolve();
                                                    }
                                                  }).then(function(){

                                                    // Now transfer the funds back to checking
                                                    console.log('Starting reverse transfer back to checking');

                                                    // Scroll back to the transfer form
                                                    return $browser.findElement($driver.By.css('input[type="number"]')).then(function(amountField){
                                                      console.log('Found amount field for reverse transfer');

                                                      // Clear and enter the same amount
                                                      return amountField.clear().then(function(){
                                                        return amountField.sendKeys('100').then(function(){
                                                          console.log('Entered reverse transfer amount: $100');

                                                          // Find the "From" dropdown and select savings
                                                          return $browser.findElement($driver.By.id('from-account-select')).then(function(fromSelect){
                                                            console.log('Found from account dropdown for reverse transfer');

                                                            return fromSelect.click().then(function(){
                                                              console.log('Opened from account dropdown');

                                                              return $browser.sleep(500).then(function(){

                                                                // Select savings as from account
                                                                return $browser.findElement($driver.By.css('li[data-value="savings"]')).then(function(savingsOption){
                                                                  return savingsOption.click().then(function(){
                                                                    console.log('Selected savings as from account');

                                                                    // Wait for the dropdown to close before clicking the next one
                                                                    return $browser.sleep(1000).then(function(){

                                                                      // Find the "To" dropdown and select checking
                                                                      return $browser.findElement($driver.By.id('to-account-select')).then(function(toSelect){
                                                                        console.log('Found to account dropdown');

                                                                        return toSelect.click().then(function(){
                                                                          console.log('Opened to account dropdown');

                                                                          return $browser.sleep(500).then(function(){

                                                                            // Select checking as to account
                                                                            return $browser.findElement($driver.By.css('li[data-value="checking"]')).then(function(checkingOption){
                                                                              return checkingOption.click().then(function(){
                                                                                console.log('Selected checking as to account');

                                                                                // Click the Complete Transfer button again
                                                                                return $browser.findElement($driver.By.css('button[type="submit"]')).then(function(transferButton){
                                                                                  console.log('Found Complete Transfer button for reverse transfer');

                                                                                  return transferButton.click().then(function(){
                                                                                    console.log('Clicked Complete Transfer button for reverse transfer');

                                                                                    // Wait for success message
                                                                                    return $browser.sleep(2000).then(function(){
                                                                                      console.log('Reverse transfer completed');
                                                                                    });
                                                                                  });
                                                                                });
                                                                              });
                                                                            });
                                                                          });
                                                                        });
                                                                      });
                                                                    });
                                                                  });
                                                                });
                                                              });
                                                            });
                                                          });
                                                        });
                                                      });
                                                    });
                                                  });
                                                });
                                              });
                                            });
                                          });
                                        });
                                      });
                                    });
                                  });
                                });
                              });
                            });
                          });
                        });
                      });
                    });
                  });
                });
              });
            });
          });
        });
      });
    });
  });
}).catch(function(error){
  console.error('Script failed with error:', error);
  throw error;
});
