document.addEventListener('DOMContentLoaded', () => {
  const noSetsEl = document.getElementById('no-sets');
  const setsContainerEl = document.getElementById('sets-container');
  const setsListEl = document.getElementById('sets-list');
  const clearBtn = document.getElementById('clear-btn');
  const setCountEl = document.getElementById('set-count');
  
  const importBtn = document.getElementById('import-btn');
  const fillAllBtn = document.getElementById('fill-all-btn');
  const statusNotice = document.getElementById('status-notice');

  let savedPredictions = [];

  function loadPredictions() {
    chrome.storage.local.get({ lottoPredictions: [] }, (result) => {
      savedPredictions = result.lottoPredictions;

      if (savedPredictions.length === 0) {
        noSetsEl.classList.remove('hidden');
        setsContainerEl.classList.add('hidden');
        clearBtn.classList.add('hidden');
        if (fillAllBtn) fillAllBtn.classList.add('hidden');
      } else {
        noSetsEl.classList.add('hidden');
        setsContainerEl.classList.remove('hidden');
        clearBtn.classList.remove('hidden');
        setCountEl.textContent = savedPredictions.length;

        // Clear existing items
        setsListEl.innerHTML = '';

        savedPredictions.forEach((pred, index) => {
          const card = document.createElement('div');
          card.className = 'prediction-card';

          const sortedNumbers = [...pred.numbers].sort((a, b) => a - b);
          const mainBallsHtml = sortedNumbers
            .map(num => `<span class="ball">${num}</span>`)
            .join('');

          card.innerHTML = `
            <div class="card-header">
              <span class="set-index">Set #${index + 1}</span>
              <span class="strategy-badge">${pred.strategy || 'AI Method'}</span>
            </div>
            <div class="number-row">
              <div class="numbers-grid">
                ${mainBallsHtml}
              </div>
              <div class="strong-ball-container">
                <span class="strong-label">Strong</span>
                <span class="ball strong">${pred.strong_number}</span>
              </div>
            </div>
          `;
          setsListEl.appendChild(card);
        });
      }
      
      // Check active tab state whenever predictions are loaded
      checkTabState();
    });
  }

  function checkTabState() {
    // Note: Using lastFocusedWindow: true is much more robust for popups than currentWindow: true
    chrome.tabs.query({ active: true, lastFocusedWindow: true }, (tabs) => {
      if (tabs.length === 0) {
        console.log("No active tab found.");
        return;
      }
      const activeTab = tabs[0];
      const url = activeTab.url || '';
      console.log("Active Tab URL detected:", url);

      // Hide actions by default
      importBtn.classList.add('hidden');
      fillAllBtn.classList.add('hidden');

      if (url.includes('/predict')) {
        importBtn.classList.remove('hidden');
        statusNotice.className = 'status-banner success';
        statusNotice.textContent = '⚡ You are on LottoFire! Click "Import All" to save your predictions.';
      } else if (url.includes('lottosheli.co.il')) {
        if (savedPredictions.length > 0) {
          fillAllBtn.classList.remove('hidden');
          statusNotice.className = 'status-banner success';
          statusNotice.textContent = '🚀 Ready to fill! Click "Auto-Fill All" to populate boards.';
        } else {
          statusNotice.className = 'status-banner info';
          statusNotice.textContent = 'ℹ️ Visit LottoFire predictions page first to copy numbers.';
        }
      } else {
        statusNotice.className = 'status-banner info';
        statusNotice.textContent = 'ℹ️ Visit LottoFire to copy predictions or LottoSheli to fill them.';
      }
    });
  }

  // Action: Import predictions from page
  importBtn.addEventListener('click', () => {
    chrome.tabs.query({ active: true, lastFocusedWindow: true }, (tabs) => {
      if (tabs.length === 0) return;
      const activeTab = tabs[0];

      chrome.scripting.executeScript({
        target: { tabId: activeTab.id },
        func: () => {
          const cards = document.querySelectorAll('.prediction-card');
          const results = [];
          
          cards.forEach((card) => {
            let mainNumbers = [];
            const ballEls = card.querySelectorAll('[data-number]');
            if (ballEls.length > 0) {
              ballEls.forEach(el => {
                const val = parseInt(el.getAttribute('data-number'), 10);
                if (!isNaN(val)) mainNumbers.push(val);
              });
            } else {
              const fallbackEls = card.querySelectorAll('.lottery-numbers .ball');
              fallbackEls.forEach(el => {
                const val = parseInt(el.textContent.trim(), 10);
                if (!isNaN(val)) mainNumbers.push(val);
              });
            }

            let strongNumber = null;
            const strongEl = card.querySelector('[data-strong]');
            if (strongEl) {
              strongNumber = parseInt(strongEl.getAttribute('data-strong'), 10);
            } else {
              const fallbackStrong = card.querySelector('.ball.strong');
              if (fallbackStrong) {
                strongNumber = parseInt(fallbackStrong.textContent.trim(), 10);
              }
            }

            const strategyEl = card.querySelector('.strategy-badge');
            const strategy = strategyEl ? strategyEl.textContent.trim() : 'AI Prediction';

            if (mainNumbers.length > 0 && strongNumber) {
              results.push({
                numbers: mainNumbers,
                strong_number: strongNumber,
                strategy: strategy
              });
            }
          });
          return results;
        }
      }, (results) => {
        if (chrome.runtime.lastError) {
          console.error("Execution error:", chrome.runtime.lastError);
          return;
        }

        if (results && results[0] && results[0].result) {
          const scrapedSets = results[0].result;
          if (scrapedSets.length > 0) {
            chrome.storage.local.get({ lottoPredictions: [] }, (storage) => {
              const currentSets = storage.lottoPredictions;
              
              // Combine and prevent duplicates
              scrapedSets.forEach(newSet => {
                const isDuplicate = currentSets.some(existing => 
                  existing.strong_number === newSet.strong_number && 
                  existing.numbers.length === newSet.numbers.length &&
                  existing.numbers.every((v, i) => v === newSet.numbers[i])
                );
                if (!isDuplicate) {
                  currentSets.push(newSet);
                }
              });

              chrome.storage.local.set({ lottoPredictions: currentSets }, () => {
                loadPredictions();
                
                const originalText = importBtn.textContent;
                importBtn.textContent = '✅ Imported!';
                importBtn.style.background = '#10b981';
                setTimeout(() => {
                  importBtn.textContent = originalText;
                  importBtn.style.background = '';
                }, 2000);
              });
            });
          } else {
            statusNotice.className = 'status-banner error';
            statusNotice.textContent = '❌ No predictions found on this page. Generate some first.';
          }
        }
      });
    });
  });

  // Action: Auto-Fill All Boards
  fillAllBtn.addEventListener('click', () => {
    chrome.tabs.query({ active: true, lastFocusedWindow: true }, (tabs) => {
      if (tabs.length === 0) return;
      const activeTab = tabs[0];

      statusNotice.className = 'status-banner info';
      statusNotice.textContent = '⏳ Auto-filling boards sequentially... Please wait.';
      fillAllBtn.disabled = true;

      // Send message to the content script on the tab to perform filling
      chrome.tabs.sendMessage(activeTab.id, { 
        action: "fill-all-boards", 
        predictions: savedPredictions 
      }, (response) => {
        fillAllBtn.disabled = false;
        
        if (chrome.runtime.lastError) {
          statusNotice.className = 'status-banner error';
          statusNotice.textContent = '❌ Failed to communicate with tab. Refresh the page and try again.';
          console.error("Tab communication error:", chrome.runtime.lastError);
          return;
        }

        if (response && response.success) {
          statusNotice.className = 'status-banner success';
          statusNotice.textContent = `✅ Successfully filled ${response.filledCount} drawing boards!`;
          
          // Flash the button green
          const originalText = fillAllBtn.textContent;
          fillAllBtn.textContent = '🚀 Filled!';
          fillAllBtn.style.background = '#10b981';
          setTimeout(() => {
            fillAllBtn.textContent = originalText;
            fillAllBtn.style.background = '';
          }, 2000);
        } else {
          statusNotice.className = 'status-banner error';
          statusNotice.textContent = `❌ Error: ${response ? response.error : 'Unknown filling error'}`;
        }
      });
    });
  });

  // Clear all sets
  clearBtn.addEventListener('click', () => {
    chrome.storage.local.set({ lottoPredictions: [] }, () => {
      loadPredictions();
    });
  });

  // Initial load
  loadPredictions();
});
