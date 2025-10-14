// Timesheet JavaScript for Tabular Format

let rowCount = 0;

// Add a new row to the table
function addRow() {
    rowCount++;
    const tbody = document.getElementById('timesheetBody');
    
    const row = document.createElement('tr');
    row.innerHTML = `
        <td><input type="date" class="entry-date" required></td>
        <td><input type="text" class="entry-project" placeholder="Project/Client name" required></td>
        <td>
            <select class="entry-activity" required>
                <option value="">Select</option>
                <option value="Client Meeting">Client Meeting</option>
                <option value="Research & Analysis">Research & Analysis</option>
                <option value="Portfolio Review">Portfolio Review</option>
                <option value="Market Research">Market Research</option>
                <option value="Report Writing">Report Writing</option>
                <option value="Administrative">Administrative</option>
                <option value="Training">Training</option>
                <option value="Other">Other</option>
            </select>
        </td>
        <td><input type="number" class="entry-hours" min="0" max="24" step="0.5" placeholder="0.0" required></td>
        <td><textarea class="entry-description" placeholder="Description of work" required></textarea></td>
        <td><button type="button" class="btn-delete" onclick="deleteRow(this)">Delete</button></td>
    `;
    
    tbody.appendChild(row);
    
    // Add event listener to hours input for total calculation
    const hoursInput = row.querySelector('.entry-hours');
    hoursInput.addEventListener('input', updateTotal);
    
    // Smooth scroll to new row
    row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Delete a row from the table
function deleteRow(button) {
    const row = button.closest('tr');
    row.style.opacity = '0';
    row.style.transform = 'translateX(-20px)';
    
    setTimeout(() => {
        row.remove();
        updateTotal();
        
        // Add at least one row if table is empty
        if (document.getElementById('timesheetBody').children.length === 0) {
            addRow();
        }
    }, 300);
}

// Update total hours
function updateTotal() {
    const hoursInputs = document.querySelectorAll('.entry-hours');
    let totalHours = 0;
    
    hoursInputs.forEach(input => {
        const value = parseFloat(input.value) || 0;
        if (value > 0) {
            totalHours += value;
        }
    });
    
    document.getElementById('totalHours').textContent = totalHours.toFixed(1);
}

// Clear the entire form
function clearForm() {
    if (confirm('Are you sure you want to clear all entries? This cannot be undone.')) {
        // Clear employee info
        document.getElementById('employeeName').value = '';
        document.getElementById('employeeId').value = '';
        document.getElementById('department').value = '';
        document.getElementById('weekEnding').value = '';
        document.getElementById('additionalNotes').value = '';
        
        // Clear all rows
        const tbody = document.getElementById('timesheetBody');
        tbody.innerHTML = '';
        rowCount = 0;
        
        // Add one empty row
        addRow();
        
        // Update total
        updateTotal();
        
        // Hide success message if visible
        document.getElementById('successMessage').style.display = 'none';
    }
}

// Validate form data
function validateForm() {
    const employeeName = document.getElementById('employeeName').value.trim();
    const employeeId = document.getElementById('employeeId').value.trim();
    const department = document.getElementById('department').value;
    const weekEnding = document.getElementById('weekEnding').value;
    
    if (!employeeName || !employeeId || !department || !weekEnding) {
        alert('Please fill in all employee information fields.');
        return false;
    }
    
    const rows = document.querySelectorAll('#timesheetBody tr');
    
    if (rows.length === 0) {
        alert('Please add at least one time entry.');
        return false;
    }
    
    let hasValidEntry = false;
    
    for (let row of rows) {
        const date = row.querySelector('.entry-date').value;
        const project = row.querySelector('.entry-project').value.trim();
        const activity = row.querySelector('.entry-activity').value;
        const hours = row.querySelector('.entry-hours').value;
        const description = row.querySelector('.entry-description').value.trim();
        
        if (date && project && activity && hours && description) {
            hasValidEntry = true;
            
            // Validate hours range
            const hoursNum = parseFloat(hours);
            if (hoursNum <= 0 || hoursNum > 24) {
                alert('Hours must be between 0 and 24.');
                return false;
            }
        }
    }
    
    if (!hasValidEntry) {
        alert('Please complete at least one time entry with all required fields.');
        return false;
    }
    
    return true;
}

// Submit timesheet
function submitTimesheet() {
    if (!validateForm()) {
        return;
    }
    
    // Collect form data
    const timesheetData = {
        employee: {
            name: document.getElementById('employeeName').value.trim(),
            id: document.getElementById('employeeId').value.trim(),
            department: document.getElementById('department').value,
            weekEnding: document.getElementById('weekEnding').value
        },
        entries: [],
        additionalNotes: document.getElementById('additionalNotes').value.trim(),
        submittedAt: new Date().toISOString()
    };
    
    // Collect all time entries from table
    const rows = document.querySelectorAll('#timesheetBody tr');
    rows.forEach((row, index) => {
        const date = row.querySelector('.entry-date').value;
        const project = row.querySelector('.entry-project').value.trim();
        const activity = row.querySelector('.entry-activity').value;
        const hours = parseFloat(row.querySelector('.entry-hours').value);
        const description = row.querySelector('.entry-description').value.trim();
        
        if (date && project && activity && hours && description) {
            timesheetData.entries.push({
                rowNumber: index + 1,
                date,
                project,
                activity,
                hours,
                description
            });
        }
    });
    
    // Calculate total
    timesheetData.totalHours = parseFloat(document.getElementById('totalHours').textContent);
    
    // Log to console (in production, this would be sent to a server)
    console.log('Timesheet Data:', JSON.stringify(timesheetData, null, 2));
    
    // Show success message
    const successMessage = document.getElementById('successMessage');
    successMessage.style.display = 'block';
    successMessage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    // In a real application, you would send this data to your backend:
    // fetch('/api/timesheet', {
    //     method: 'POST',
    //     headers: { 'Content-Type': 'application/json' },
    //     body: JSON.stringify(timesheetData)
    // })
    // .then(response => response.json())
    // .then(data => {
    //     successMessage.style.display = 'block';
    // })
    // .catch(error => {
    //     alert('Error submitting timesheet: ' + error.message);
    // });
    
    // Hide success message after 5 seconds
    setTimeout(() => {
        successMessage.style.display = 'none';
    }, 5000);
}

// Initialize: Add event listeners when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Set week ending to current Friday
    const today = new Date();
    const dayOfWeek = today.getDay();
    const daysUntilFriday = (5 - dayOfWeek + 7) % 7 || 7;
    const nextFriday = new Date(today);
    nextFriday.setDate(today.getDate() + daysUntilFriday);
    
    const weekEndingInput = document.getElementById('weekEnding');
    weekEndingInput.valueAsDate = nextFriday;
    
    // Add initial row
    addRow();
});
