/**
 * Paper Generation and Attempt Interactivity Scripts
 */

document.addEventListener('DOMContentLoaded', () => {
    
    // =========================================================================
    // 1. Live Adaptive Allocation Preview in Generate Paper Form
    // =========================================================================
    const generateForm = document.getElementById('generatePaperForm');
    const previewContainer = document.getElementById('adaptivePreviewContainer');
    
    if (generateForm && previewContainer) {
        const chapterCheckboxes = generateForm.querySelectorAll('input[name="chapter_ids"]');
        const marksInput = document.getElementById('total_marks');
        
        async function updateLivePreview() {
            const selectedChapters = Array.from(chapterCheckboxes)
                .filter(cb => cb.checked)
                .map(cb => parseInt(cb.value));
                
            const totalMarks = parseInt(marksInput ? marksInput.value : 30) || 30;
            
            if (selectedChapters.length === 0) {
                previewContainer.innerHTML = `
                    <div class="text-muted small text-center py-4">
                        <i class="bi bi-info-circle me-1 text-primary"></i> Pick a chapter to see how the marks will be shared.
                    </div>`;
                return;
            }
            
            try {
                const response = await fetch('/api/preview-adaptive-allocation', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        chapter_ids: selectedChapters,
                        total_marks: totalMarks
                    })
                });
                
                const data = await response.json();
                if (data.success) {
                    const levelText = { Weak: 'Needs practice', Average: 'Getting better', Strong: 'Strong', Unattempted: 'Not tried yet' };
                    let html = '<div class="split-list">';

                    data.allocations.forEach(item => {
                        html += `
                            <div class="split-row">
                                <span class="split-name">${item.chapter_name}
                                    <span class="split-level">${levelText[item.status] || ''}</span>
                                </span>
                                <div class="split-bar"><div style="width: ${item.percentage}%;"></div></div>
                                <span class="split-val">${item.allocated_marks} marks</span>
                            </div>`;
                    });
                    html += '</div>';

                    if (data.explanations && data.explanations.length > 0) {
                        html += `<details class="mt-3"><summary class="small text-primary fw-semibold">Why this split?</summary>
                            <ul class="small text-secondary mt-2 mb-0 ps-3">`;
                        data.explanations.forEach(exp => {
                            html += `<li class="mb-1">${exp.replace(/\*\*/g, '')}</li>`;
                        });
                        html += '</ul></details>';
                    }

                    previewContainer.innerHTML = html;
                }
            } catch (err) {
                console.error('Error fetching preview:', err);
            }
        }
        
        chapterCheckboxes.forEach(cb => cb.addEventListener('change', updateLivePreview));
        if (marksInput) marksInput.addEventListener('input', updateLivePreview);
        
        updateLivePreview();
    }

    // =========================================================================
    // 2. Real-time Marks Calculation & Validation in Attempt Form
    // =========================================================================
    const attemptForm = document.getElementById('attemptPaperForm');
    if (attemptForm) {
        const markInputs = attemptForm.querySelectorAll('.mark-input');
        const scoreCounter = document.getElementById('liveTotalScore');
        const pctDisplay = document.getElementById('livePercentageDisplay');
        const answeredCountEl = document.getElementById('answeredCount');
        const progressEl = document.getElementById('answeredProgress');
        const totalMarksMax = parseFloat(scoreCounter ? scoreCounter.dataset.maxMarks : 0) || 0;
        const totalQuestions = markInputs.length;
        
        function calculateTotalMarks() {
            let currentTotal = 0.0;
            let answeredCount = 0;
            
            markInputs.forEach(input => {
                const max = parseFloat(input.dataset.maxMark) || 0;
                const val = parseFloat(input.value);
                
                if (!isNaN(val)) {
                    if (val < 0 || val > max) {
                        input.classList.add('is-invalid');
                    } else {
                        input.classList.remove('is-invalid');
                        currentTotal += val;
                    }
                }
                
                // Count as answered if student changed from 0 or entered answer
                const qCard = input.closest('.question-attempt-card');
                const answerText = qCard ? qCard.querySelector('.student-answer-input')?.value.trim() : '';
                if (val > 0 || (answerText && answerText.length > 0)) {
                    answeredCount++;
                }
            });
            
            if (scoreCounter) {
                scoreCounter.textContent = currentTotal.toFixed(1).replace('.0', '');
            }

            if (pctDisplay && totalMarksMax > 0) {
                const pct = Math.round((currentTotal / totalMarksMax) * 100);
                pctDisplay.textContent = `${pct}% Achieved`;
            }

            if (answeredCountEl) {
                answeredCountEl.textContent = `${answeredCount} / ${totalQuestions}`;
            }

            if (progressEl && totalQuestions > 0) {
                const progressPct = Math.round((answeredCount / totalQuestions) * 100);
                progressEl.style.width = `${progressPct}%`;
            }
        }
        
        markInputs.forEach(input => {
            input.addEventListener('input', calculateTotalMarks);
        });

        document.querySelectorAll('.student-answer-input').forEach(ta => {
            ta.addEventListener('input', calculateTotalMarks);
        });
        
        // Initial calculation
        calculateTotalMarks();
    }
});
