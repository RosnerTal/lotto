(function() {
  console.log("LottoSheli Auto-Filler Content Script Active.");

  // Find board selector tabs (e.g., "1 טבלה", "2 טבלה", "טבלה 1")
  function findBoardTabs() {
    const allElements = document.querySelectorAll('button, [role="button"], div, span, a');
    const tabCandidates = [];
    
    allElements.forEach(el => {
      const text = el.textContent.trim();
      
      // Match if text contains the Hebrew word "טבלה" (Table) and any digits (e.g., "1 טבלה")
      if (text.includes("טבלה") && /\d/.test(text)) {
        // Enforce a maximum text length to avoid matching large paragraphs
        if (text.length < 30) {
          tabCandidates.push(el);
        }
      }
    });
    
    // Filter to keep only the leaf-most elements that contain the target text.
    // If element A contains element B, and both are candidates, we discard A and keep B.
    // This allows us to target the specific tab-row container even if text is split into spans.
    const finalTabs = tabCandidates.filter(el1 => {
      return !tabCandidates.some(el2 => el1 !== el2 && el1.contains(el2));
    });

    const tabs = finalTabs.map(el => {
      return { element: el, text: el.textContent.trim() };
    });
    
    // Sort tabs by the number in their text (extracting digits)
    tabs.sort((a, b) => {
      const numA = parseInt(a.text.replace(/\D/g, ''), 10) || 0;
      const numB = parseInt(b.text.replace(/\D/g, ''), 10) || 0;
      return numA - numB;
    });
    
    return tabs;
  }

  // Find lottery board grids on the page using visual parent clustering
  function findLottoBoards() {
    const allElements = document.querySelectorAll('button, [role="button"], div, span');
    
    // We want to find the leaf-most elements containing numeric text
    const numberLeaves = [];
    allElements.forEach(el => {
      const text = el.textContent.trim();
      if (/^\d+$/.test(text)) {
        // If a child has the exact same text, it means this element is just a container wrapper,
        // and we want to target the actual leaf element inside instead.
        const hasChildWithSameText = Array.from(el.children).some(child => 
          child.textContent.trim() === text
        );
        
        if (!hasChildWithSameText) {
          const num = parseInt(text, 10);
          numberLeaves.push({ element: el, value: num });
        }
      }
    });

    // Cluster leaves by parent hierarchy up to 7 levels (handles deep React nesting)
    const parentClusters = new Map();
    numberLeaves.forEach(leaf => {
      let parent = leaf.element.parentElement;
      for (let depth = 0; depth < 7 && parent; depth++) {
        if (!parentClusters.has(parent)) {
          parentClusters.set(parent, []);
        }
        parentClusters.get(parent).push(leaf);
        parent = parent.parentElement;
      }
    });

    const mainGridCandidates = [];
    const strongGridCandidates = [];

    parentClusters.forEach((leaves, container) => {
      const uniqueMain = new Set();
      const uniqueStrong = new Set();
      
      leaves.forEach(leaf => {
        if (leaf.value >= 1 && leaf.value <= 37) {
          uniqueMain.add(leaf.value);
        }
        if (leaf.value >= 1 && leaf.value <= 7) {
          uniqueStrong.add(leaf.value);
        }
      });

      // Main Grid criteria (35+ unique main numbers)
      if (uniqueMain.size >= 35) {
        mainGridCandidates.push({ container, size: uniqueMain.size });
      }
      
      // Strong Grid criteria (exactly 7 unique strong numbers, and <= 15 main numbers to avoid main-grid overlaps)
      if (uniqueStrong.size === 7 && uniqueMain.size <= 15) {
        strongGridCandidates.push({ container });
      }
    });

    // Keep leaf-most containers (discard parent nodes that cluster multiple grids)
    const finalMainGrids = mainGridCandidates.filter(c1 => {
      return !mainGridCandidates.some(c2 => c1 !== c2 && c1.container.contains(c2.container));
    });

    const finalStrongGrids = strongGridCandidates.filter(c1 => {
      return !strongGridCandidates.some(c2 => c1 !== c2 && c1.container.contains(c2.container));
    });

    // Pair Main Grids with closest Strong Grids based on spatial proximity
    const boards = [];
    finalMainGrids.forEach((main, index) => {
      let closestStrong = null;
      let minDistance = Infinity;

      const rectMain = main.container.getBoundingClientRect();
      const mainCenter = { 
        x: rectMain.left + rectMain.width / 2, 
        y: rectMain.top + rectMain.height / 2 
      };

      finalStrongGrids.forEach(strong => {
        const rectStrong = strong.container.getBoundingClientRect();
        const strongCenter = { 
          x: rectStrong.left + rectStrong.width / 2, 
          y: rectStrong.top + rectStrong.height / 2 
        };

        const dist = Math.hypot(mainCenter.x - strongCenter.x, mainCenter.y - strongCenter.y);
        if (dist < minDistance) {
          minDistance = dist;
          closestStrong = strong;
        }
      });

      boards.push({
        index: index + 1,
        mainGrid: main.container,
        strongGrid: closestStrong ? closestStrong.container : null
      });
    });

    // Sort boards visually: Top-to-Bottom row by row, and Right-to-Left (RTL) within each row
    boards.sort((a, b) => {
      const rectA = a.mainGrid.getBoundingClientRect();
      const rectB = b.mainGrid.getBoundingClientRect();
      
      const rowDiff = rectA.top - rectB.top;
      // If they are on different rows (more than 50px vertical gap)
      if (Math.abs(rowDiff) > 50) {
        return rowDiff; // Top to bottom
      }
      
      // If they are on the same row, sort right-to-left (RTL)
      return rectB.left - rectA.left;
    });

    // Re-index boards after sorting
    boards.forEach((b, i) => {
      b.index = i + 1;
    });

    return boards;
  }

  // Find best clickable element representing a specific number in a grid container
  function findBestClickableNumberElement(gridContainer, number) {
    if (!gridContainer) return null;
    
    // Find all descendants whose text matches exactly (or matches single digit with leading zero)
    const candidates = Array.from(gridContainer.querySelectorAll('*'))
      .filter(el => {
        const text = el.textContent.trim();
        return text === String(number) || text === ('0' + number);
      });
      
    if (candidates.length === 0) return null;
    
    // 1. Prefer button tags or elements explicitly marked with role="button" or containing "button" class
    const buttonMatch = candidates.find(el => 
      el.tagName === 'BUTTON' || 
      el.getAttribute('role') === 'button' || 
      el.classList.contains('button')
    );
    if (buttonMatch) return buttonMatch;
    
    // 2. Otherwise, return the leaf-most matching element (fewest children)
    candidates.sort((a, b) => a.querySelectorAll('*').length - b.querySelectorAll('*').length);
    return candidates[0];
  }

  // Simulate mouse clicks correctly for React/Next.js state bindings
  function simulateClick(element) {
    if (!element) return false;
    try {
      console.log("[LottoFire Auto-Filler] Clicking element:", element);
      const eventOptions = { bubbles: true, cancelable: true, view: window };
      element.dispatchEvent(new MouseEvent('mousedown', eventOptions));
      element.dispatchEvent(new MouseEvent('mouseup', eventOptions));
      element.click();
      element.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    } catch (e) {
      console.error("[LottoFire Auto-Filler] Click simulation error:", e);
      return false;
    }
  }

  // Async fill function with safety delay
  async function fillBoard(board, numbers, strongNumber) {
    if (!board) return { success: false, error: "Board not found." };
    
    // Activate the board by clicking it first
    simulateClick(board.mainGrid);
    await new Promise(resolve => setTimeout(resolve, 200));
    
    let mainFilled = 0;
    
    // Click main numbers one by one
    for (const num of numbers) {
      const btn = findBestClickableNumberElement(board.mainGrid, num);
      if (btn) {
        const ok = simulateClick(btn);
        if (ok) mainFilled++;
        await new Promise(resolve => setTimeout(resolve, 120)); // Delay between clicks
      } else {
        console.warn(`[LottoFire Auto-Filler] Main number ${num} element not found in grid.`);
      }
    }

    // Click strong number
    let strongFilled = false;
    if (board.strongGrid) {
      const strongBtn = findBestClickableNumberElement(board.strongGrid, strongNumber);
      if (strongBtn) {
        strongFilled = simulateClick(strongBtn);
      } else {
        console.warn(`[LottoFire Auto-Filler] Strong number ${strongNumber} element not found in grid.`);
      }
    }

    return {
      success: mainFilled >= 5 && strongFilled,
      mainCount: mainFilled,
      strongSuccess: strongFilled
    };
  }

  // Fill all boards sequentially
  async function fillAllBoards(predictions) {
    console.log("[LottoFire Auto-Filler] Running board scan...");
    
    // Check if we have board tabs (e.g., "1 טבלה", "2 טבלה")
    const tabs = findBoardTabs();
    console.log(`[LottoFire Auto-Filler] Found ${tabs.length} board tabs.`);
    
    if (tabs.length > 0) {
      // Tabbed layout filling (mobile responsive or panel switching)
      const fillCount = Math.min(predictions.length, tabs.length);
      console.log(`[LottoFire Auto-Filler] Filling ${fillCount} boards via tab clicks.`);
      
      for (let i = 0; i < fillCount; i++) {
        const tab = tabs[i];
        const pred = predictions[i];
        
        console.log(`[LottoFire Auto-Filler] Switching to tab: ${tab.text}`);
        simulateClick(tab.element);
        await new Promise(resolve => setTimeout(resolve, 400)); // wait for tab rendering
        
        // Find visible grids
        const currentBoards = findLottoBoards();
        if (currentBoards.length > 0) {
          // Fill the first visible grid (which corresponds to the active tab)
          await fillBoard(currentBoards[0], pred.numbers, pred.strong_number);
        } else {
          console.error(`[LottoFire Auto-Filler] Grid not found after clicking tab ${tab.text}`);
        }
        await new Promise(resolve => setTimeout(resolve, 500));
      }
      return fillCount;
    } else {
      // Static grid layout filling (side-by-side desktop panels)
      const boards = findLottoBoards();
      console.log(`[LottoFire Auto-Filler] Found ${boards.length} total boards on the page.`);
      
      if (boards.length === 0) {
        throw new Error("No lottery drawing boards found on the page.");
      }

      const fillCount = Math.min(predictions.length, boards.length);
      console.log(`[LottoFire Auto-Filler] Filling ${fillCount} boards sequentially.`);

      for (let i = 0; i < fillCount; i++) {
        const board = boards[i];
        const pred = predictions[i];
        
        console.log(`[LottoFire Auto-Filler] Auto-filling Board #${board.index} (visual index ${i+1}) with Set #${i+1}`);
        await fillBoard(board, pred.numbers, pred.strong_number);
        await new Promise(resolve => setTimeout(resolve, 500));
      }

      return fillCount;
    }
  }

  // Listen to messages from popup.js
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "fill-all-boards") {
      fillAllBoards(request.predictions)
        .then(count => {
          sendResponse({ success: true, filledCount: count });
        })
        .catch(err => {
          sendResponse({ success: false, error: err.message });
        });
      return true; // async channel open
    }
  });
})();
