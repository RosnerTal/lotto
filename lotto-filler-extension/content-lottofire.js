(function() {
  // Check if we are on the LottoFire predict page
  if (!window.location.pathname.includes('/predict')) {
    return;
  }

  console.log("LottoFire Auto-Filler Content Script Loaded.");

  // Apply CSS styling for the injected elements dynamically
  const style = document.createElement('style');
  style.textContent = `
    .lottofire-extension-copy-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      width: 100%;
      margin-top: 12px;
      padding: 8px 12px;
      background: rgba(139, 92, 246, 0.15);
      border: 1px dashed rgba(139, 92, 246, 0.4);
      border-radius: 8px;
      color: #c084fc;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
      font-family: inherit;
    }
    
    .lottofire-extension-copy-btn:hover {
      background: rgba(139, 92, 246, 0.3);
      border-color: rgba(139, 92, 246, 0.8);
      color: #fff;
      transform: translateY(-1px);
    }
    
    .lottofire-extension-copy-btn.copied {
      background: rgba(16, 185, 129, 0.2);
      border-color: rgba(16, 185, 129, 0.8);
      color: #34d399;
      cursor: default;
      transform: none;
    }

    .lottofire-global-bar {
      position: fixed;
      bottom: 20px;
      left: 50%;
      transform: translateX(-50%) translateY(100px);
      background: rgba(15, 23, 42, 0.85);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      padding: 12px 24px;
      border-radius: 50px;
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5), 0 0 15px rgba(139, 92, 246, 0.2);
      display: flex;
      align-items: center;
      gap: 16px;
      z-index: 10000;
      transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }

    .lottofire-global-bar.show {
      transform: translateX(-50%) translateY(0);
    }

    .lottofire-global-text {
      color: #f8fafc;
      font-size: 0.9rem;
      font-weight: 500;
    }

    .lottofire-global-btn {
      background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
      color: #fff;
      border: none;
      padding: 6px 16px;
      border-radius: 20px;
      font-size: 0.8rem;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
      transition: all 0.2s ease;
    }

    .lottofire-global-btn:hover {
      box-shadow: 0 0 10px rgba(139, 92, 246, 0.5);
      opacity: 0.95;
    }
  `;
  document.head.appendChild(style);

  // Setup Global Status Toast Bar
  const globalBar = document.createElement('div');
  globalBar.className = 'lottofire-global-bar';
  globalBar.innerHTML = `
    <span class="lottofire-global-text">Saved predictions! Ready to auto-fill.</span>
    <a href="https://lottosheli.co.il/draw/lotto" target="_blank" class="lottofire-global-btn">Open LottoSheli ➔</a>
  `;
  document.body.appendChild(globalBar);

  function showGlobalBar() {
    globalBar.classList.add('show');
  }

  // Find all prediction cards
  const cards = document.querySelectorAll('.prediction-card');
  cards.forEach((card, index) => {
    // 1. Extract numbers
    const numberBalls = card.querySelectorAll('.lottery-numbers .ball');
    const mainNumbers = [];
    numberBalls.forEach(ball => {
      const val = parseInt(ball.textContent.trim(), 10);
      if (!isNaN(val)) mainNumbers.push(val);
    });

    const strongBall = card.querySelector('.ball.strong');
    const strongNumber = strongBall ? parseInt(strongBall.textContent.trim(), 10) : null;

    const strategyEl = card.querySelector('.strategy-badge');
    const strategy = strategyEl ? strategyEl.textContent.trim() : 'AI Prediction';

    if (mainNumbers.length === 0 || !strongNumber) {
      return; // Skip if invalid card data
    }

    // 2. Create and inject "Copy to LottoSheli" button
    const copyBtn = document.createElement('button');
    copyBtn.className = 'lottofire-extension-copy-btn';
    copyBtn.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
      </svg>
      Copy to LottoSheli
    `;

    copyBtn.addEventListener('click', () => {
      // Fetch existing predictions from storage
      chrome.storage.local.get({ lottoPredictions: [] }, (result) => {
        const predictions = result.lottoPredictions;
        
        // Prepare the new prediction set
        const newSet = {
          numbers: mainNumbers,
          strong_number: strongNumber,
          strategy: strategy,
          timestamp: Date.now()
        };

        // Add to prediction list
        predictions.push(newSet);

        // Store back in chrome storage
        chrome.storage.local.set({ lottoPredictions: predictions }, () => {
          console.log("Prediction saved:", newSet);
          
          // Animate button success state
          copyBtn.classList.add('copied');
          copyBtn.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            Copied!
          `;
          copyBtn.disabled = true;

          // Show the floating notification bar
          showGlobalBar();

          // Reset button back to copy state after 3 seconds so they can copy it again if they want
          setTimeout(() => {
            copyBtn.classList.remove('copied');
            copyBtn.innerHTML = `
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              Copy to LottoSheli
            `;
            copyBtn.disabled = false;
          }, 3000);
        });
      });
    });

    card.appendChild(copyBtn);
  });
})();
