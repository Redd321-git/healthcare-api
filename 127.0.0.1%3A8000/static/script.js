// Base API configuration
const API_BASE_URL = 'http://localhost:8000';
let authToken = null;

// Sample data
let patients = [];
const patientHospitals = [];
let recordRequests = [];
const medicalRecords = [];

// Role definitions
const roles = {
    "doctor": [
        { name: "Patients", section: "patients", icon: "fa-user-injured" },
        { name: "Consultation", section: "consultation", icon: "fa-stethoscope" },
        { name: "Appointments", section: "appointments", icon: "fa-calendar-check" },
        { name: "Medical Reports", section: "reports", icon: "fa-file-medical" }
    ],
    "patient": [
        { name: "My Profile", section: "profile", icon: "fa-user" },
        { name: "Retrieve Records", section: "retrieve-records", icon: "fa-download" },
        { name: "Request Records", section: "request-records", icon: "fa-file-download" },
        { name: "Appointments", section: "patient-appointments", icon: "fa-calendar-alt" }
    ],
    "admin": [
        { name: "Patient Management", section: "patient-management", icon: "fa-user-injured" },
        { name: "Hospital Details", section: "hospital-details", icon: "fa-hospital" },
        { name: "Patient Files", section: "file-upload", icon: "fa-file-upload" },
        { name: "Find Patient File", section: "find-patient-file", icon: "fa-search" }
    ]
};

// Authentication functions
function getAuthToken() {
    return localStorage.getItem('token');
}

// API request function
async function makeApiRequest(url, method = 'GET', body = null, expectBlob = false) {
    try {
        const config = {
            method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
        };

        if (body) {
            if (body instanceof FormData) {
                // Remove Content-Type header for FormData
                delete config.headers['Content-Type'];
                config.body = body;
            } else {
                config.body = JSON.stringify(body);
            }
        }

        const response = await fetch(`${API_BASE_URL}${url}`, config);
        
        if (!response.ok) {
            if (response.status === 401) {
                // Token expired or invalid
                localStorage.removeItem('token');
                localStorage.removeItem('userRole');
                window.location.reload();
                throw new Error('Session expired. Please login again.');
            }
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        
        return expectBlob ? await response.blob(): await response.json();
    } catch (error) {
        console.error('API Request Error:', error);
        throw new Error(`API request failed: ${error.message}`);
    }
}

// File upload functionality
document.addEventListener('click', async (e) => {
    if (e.target && e.target.id === 'uploadFilesBtn') {
        const fileInput = document.getElementById('fileInput');
        const patientId = document.getElementById('filePatientSelect');
        const fileTypeSelect = document.getElementById('fileTypeSelect');
        
        if (!fileInput || !patientId || !fileTypeSelect) {
            console.error('Required elements not found');
            return;
        }
        
        const patientIdValue = patientId.value.trim();
        const fileType = fileTypeSelect.value;
        
        if (!patientIdValue) {
            showToast('Please enter a patient ID', 'error');
            return;
        }
        
        if (fileInput.files.length === 0) {
            showToast('Please select at least one file', 'error');
            return;
        }
        
        try {
            const uploadedFiles = [];
            
            for (let i = 0; i < fileInput.files.length; i++) {
                const formData = new FormData();
                formData.append('file', fileInput.files[i]);
                formData.append('patient_id', patientIdValue);
                formData.append('file_type', fileType);
                console.log(formData);
                const response = await makeApiRequest('/upload-file/','POST',formData);
                console.log("reponse feteched");
		console.log(response);

                console.log("reponse ok");
                uploadedFiles.push({
                    file_name: fileInput.files[i].name,
                    upload_date: new Date().toISOString(),
                    file_type: fileType,
                    file_id: `file_${Date.now()}_${i}`
                });
            }
            
            showToast('Files uploaded successfully!', 'success');
            // Clear the file input
            fileInput.value = '';
            
            // Update the display with the newly uploaded files
            const container = document.getElementById('uploadedFilesList');
            if (container) {
                // Get existing files
                const existingFiles = Array.from(container.querySelectorAll('.file-item')).map(item => ({
                    file_name: item.querySelector('strong').textContent,
                    upload_date: item.querySelector('small').textContent.split(' • ')[0],
                    file_type: item.querySelector('small').textContent.split(' • ')[1],
                    file_id: item.dataset.fileId
                }));
                
                // Combine existing and new files
                const allFiles = [...existingFiles, ...uploadedFiles];
                
                // Clear and re-render
                container.innerHTML = '';
                
                if (allFiles.length === 0) {
                    container.innerHTML = '<p>No files uploaded yet</p>';
                    return;
                }
                
                allFiles.forEach(file => {
                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-item';
                    fileItem.dataset.fileId = file.file_id;
                    fileItem.innerHTML = `
                        <div>
                            <strong>${file.file_name}</strong>
                            <small>${formatDate(file.upload_date)} • ${file.file_type}</small>
                        </div>
                        <div>
                            <span class="status-badge status-active">Uploaded</span>
                        </div>
                    `;
                    container.appendChild(fileItem);
                });
            }
        } catch (error) {
            console.error('Upload error:', error);
            showToast(`File upload failed: ${error.message}`, 'error');
        }
    }
});

// Toast notification function
function showToast(message, type) {
    const toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container';
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icon = document.createElement('i');
    icon.className = `toast-icon fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}`;
    
    const text = document.createElement('span');
    text.textContent = message;
    
    toast.appendChild(icon);
    toast.appendChild(text);
    toastContainer.appendChild(toast);
    document.body.appendChild(toastContainer);
    
    setTimeout(() => {
        toast.classList.add('show');
    }, 100);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            toastContainer.remove();
        }, 300);
    }, 3000);
}

// Helper function to format dates
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// Login function
async function login() {
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value.trim();
    //const role = document.getElementById("roleSelect").value;

    if (!username || !password) {
        showToast("Please enter both username and password", "error");
        return;
    }

    try {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch('/login', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
	console.log("User data received:", data);
        if (response.ok) {

            // Store the token
            localStorage.setItem("token", data.access_token);

            const meResponse = await fetch('/me', {
                method: 'GET',
                headers: {
                    Authorization:`Bearer ${data.access_token}`
                }
            });

            if (meResponse.ok) {

                const userData = await meResponse.json();
		console.log("User data received:", userData);
		const userRole = userData.role;
                localStorage.setItem("userRole", userData.role);

		connectWebSocket(data.access_token);

                // Hide login and show dashboard
                document.getElementById("loginContainer").style.display = "none";
                document.getElementById("dashboard").style.display = "flex";

                // Load dashboard
                loadDashboard(userRole);
                showToast("Login successful!", "success");

            } else {
                showToast(data.detail || "Authentication failed-", "error");
            }
            
        } else {
            showToast(data.detail || "Login failed. Please check your credentials.", "error");
        }

    } catch (error) {
        console.error('Login error:', error);
        showToast("An error occurred during login. Please try again.", "error");
    }
}

function loadDashboard(role) {
    const roleTitles = {
        "doctor": "Doctor Dashboard",
        "patient": "Patient Portal",
        "admin": "Hospital Admin"
    };
    
    document.getElementById("userRoleTitle").innerText = roleTitles[role];
    document.getElementById("sidebarTitle").innerText = roleTitles[role];
    
    let sidebar = document.getElementById("sidebarLinks");
    sidebar.innerHTML = "";
    
    roles[role].forEach(link => {
        let a = document.createElement("a");
        a.innerHTML = `<i class="fas ${link.icon}"></i> ${link.name}`;
        a.href = "#";
        a.onclick = (e) => {
            e.preventDefault();
            showSection(link.section, role);
            setActiveLink(a);
        };
        sidebar.appendChild(a);
    });
}

function setActiveLink(activeLink) {
    const links = document.querySelectorAll('#sidebarLinks a');
    links.forEach(link => link.classList.remove('active'));
    activeLink.classList.add('active');
}

function showSection(sectionId, role) {
    let content = document.getElementById("contentSection");
    const sectionTitles = {
        "patient-management": "Patient Management",
        "hospital-details": "Hospital Details",
        "file-upload": "Patient File Upload",
        "manage-users": "Staff Management",
        "appointment-scheduling": "Appointment Scheduling",
        "patient-list": "Patient List",
        "appointments": "Appointments",
        "reports": "Medical Reports",
        "prescriptions": "Prescriptions",
        "profile": "My Profile",
        "patient-appointments": "My Appointments",
        "medical-records": "My Medical Records",
        "request-records": "Request Records",
        "retrieve-records": "Retrieve Records",
        "medical-history": "Medical History",
        "find-patient-file": "Find Patient File"
    };

    // Hide the sidebar
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    sidebar.classList.remove("open");
    overlay.classList.remove("active");

    // Reset file sections visibility safely
    const fileUploadSection = document.getElementById('fileUploadSection');
    const fileRetrievalSection = document.getElementById('fileRetrievalSection');
    
    if (fileUploadSection) {
        fileUploadSection.style.display = 'none';
    }
    if (fileRetrievalSection) {
        fileRetrievalSection.style.display = 'none';
    }

    let sectionContent = '';
    
    // Handle each section type
    switch(sectionId) {
        case "patients":
            sectionContent = `
                <h2>Patients</h2>
                <div class="section-grid">
                    <div class="section-card">
                        <h3><i class="fas fa-search"></i> Search Patients</h3>
                        <input type="text" id="patientSearch" placeholder="Search by Patient ID or Name" style="width: 100%;" oninput="searchPatients()">
                        <div style="margin-top: 15px;">
                            <h4>Recent Patients</h4>
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Patient ID</th>
                                    <th>Name</th>
                                    <th>Last Visit</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="patientTableBody">
                                ${generateRecentPatientRows()}
                            </tbody>
                        </table>
                    </div>
                    </div>
                </div>
            `;
            break;
            
        
            
        case "hospital-details":
            sectionContent = `
                <h2>Hospital Details</h2>
                <div class="section-grid">
                    <div class="section-card">
                        <h3><i class="fas fa-info-circle"></i> Facility Information</h3>
                        <form id="hospitalForm">
                            <div class="form-group">
                                <label>Hospital Name</label>
                                <input type="text" id="hospitalName" placeholder="Enter hospital name">
                            </div>
                            <div class="form-group">
                                <label>Address</label>
                                <input type="text" id="hospitalAddress" placeholder="Enter hospital address">
                            </div>
                            <div class="form-group">
                                <label>Contact Number</label>
                                <input type="text" id="hospitalContact" placeholder="Enter contact number">
                            </div>
                            <div class="form-group">
                                <label>Emergency Contact</label>
                                <input type="text" id="hospitalEmergency" placeholder="Enter emergency contact">
                            </div>
                            <div class="form-group">
                                <label>Email</label>
                                <input type="email" id="hospitalEmail" placeholder="Enter hospital email">
                            </div>
                            <div class="form-group">
                                <label>Website</label>
                                <input type="url" id="hospitalWebsite" placeholder="Enter hospital website">
                            </div>
                            <button type="submit" style="width: 100%;">Save Changes</button>
                        </form>
                    </div>
                </div>
            `;
            // Load existing hospital details
            loadHospitalDetails();
            break;
            
        case "file-upload":
            sectionContent = `
                <h2>Patient File Upload</h2>
                <div class="section-grid">
                    <div class="section-card">
                        <h3><i class="fas fa-upload"></i> Upload New Files</h3>
                        <div class="file-upload" onclick="document.getElementById('fileInput').click()">
                            <i class="fas fa-cloud-upload-alt" style="font-size: 24px; color: #4facfe;"></i>
                            <p>Click to browse or drag files here</p>
                            <input type="file" id="fileInput" style="display: none;" multiple>
                        </div>
			<input type="file" id="fileInput" style="display: none;" multiple>
			<div id="selectedFilesList" style="margin-top: 10px; font-style: italic; color: #555;"></div>
                        <div style="margin-top: 15px;">
                            <label>Patient ID</label>
                            <input type="text" id="filePatientSelect" placeholder="e.g., P1001" style="width: 100%;">
                            <label style="margin-top: 10px; display: block;">File Type</label>
                            <select id="fileTypeSelect" style="width: 100%;">
                                <option value="pdf">PDF Document</option>
                                <option value="xml">XML File</option>
                                <option value="json">JSON File</option>
                                <option value="csv">CSV File</option>
                                <option value="jpg">JPG Image</option>
                            </select>
                            <button id="uploadFilesBtn" style="width: 100%; margin-top: 15px;">Upload Files</button>
                        </div>
                    </div>
                    <div class="section-card">
                        <h3><i class="fas fa-file-upload"></i> Uploaded Files</h3>
                        <div id="uploadedFilesList" class="file-preview">
                            <!-- Files will be listed here -->
                        </div>
                    </div>
                </div>
            `;
            break;
            
        case "profile":
            sectionContent = `
                <h2>My Profile</h2>
                <form id="patientProfileForm" class="section-card" style="max-width: 600px; margin: 0 auto;">
                    <div class="form-group">
                        <label>First Name</label>
                        <input type="text" id="firstName" required>
                    </div>
                    <div class="form-group">
                        <label>Last Name</label>
                        <input type="text" id="lastName" required>
                    </div>
                    <div class="form-group">
                        <label>Date of Birth</label>
                        <input type="date" id="dob" required>
                    </div>
                    <div class="form-group">
                        <label>Gender</label>
                        <select id="gender" required>
                            <option value="">Select Gender</option>
                            <option>Male</option>
                            <option>Female</option>
                            <option>Other</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Contact Number</label>
                        <input type="tel" id="contactNumber">
                    </div>
                    <div class="form-group">
                        <label>Email</label>
                        <input type="email" id="email">
                    </div>
                    <div class="form-group">
                        <label>Address</label>
                        <textarea id="address" rows="3"></textarea>
                    </div>
                    <div class="form-group">
                        <label>Emergency Contact</label>
                        <input type="text" id="emergencyContact">
                    </div>
                    <button type="submit">Save Profile</button>
                </form>
            `;
            break;
            
        case "medical-records":
            sectionContent = `
                <h2>My Medical Records</h2>
                <div style="margin-bottom: 20px;">
                    <p>View and manage your medical records from different healthcare providers.</p>
                </div>
                <div class="section-card" id="fileRetrievalSection">
                    <h3><i class="fas fa-file-download"></i> My Files</h3>
                    <div style="margin-bottom: 15px;">
                        <label>Filter by File Type</label>
                        <select id="fileFilterSelect" style="width: 100%;" onchange="filterPatientFiles()">
                            <option value="all">All Types</option>
                            <option value="medical_report">Medical Reports</option>
                            <option value="lab_result">Lab Results</option>
                            <option value="prescription">Prescriptions</option>
                            <option value="imaging">Imaging</option>
                        </select>
                    </div>
                    <div id="patientFilesList" class="file-preview">
                        <!-- Files will be listed here -->
                    </div>
                </div>
            `;
            loadPatientFiles();
            break;
            
        	case "patient-appointments":
		sectionContent = `
			<h2>Book an Appointment</h2>
			<form id="appointmentForm" class="section-card" style="max-width: 600px; margin: 0 auto;">
				<div class="form-group">
					<label>Doctor ID</label>
					<input type="text" id="doctorId" placeholder="Enter Doctor ID" required>
				</div>
				<div class="form-group">
					<label>Preferred Date</label>
					<input type="date" id="appointmentDate" required>
				</div>
				<button type="submit">Book Appointment</button>
			</form>
			<div id="appointmentSuccess" class="alert alert-success" style="display: none; margin-top: 15px;">
				Appointment booked successfully and file access granted!
			</div>
		`;

    // Add JavaScript for form submission
		setTimeout(() => {
			const form = document.getElementById("appointmentForm");
			form.addEventListener("submit", async (e) => {
			    e.preventDefault();
	    		const doctorId = document.getElementById("doctorId").value.trim();
	    		const appointmentDate = document.getElementById("appointmentDate").value;
		    	if (!doctorId || !appointmentDate) {
			    	showToast("Please provide both Doctor ID and Date.", "error");
				    return;
		    	}	

			    try {
				    const response = await makeApiRequest(`/give_permission/?doctor_id=${encodeURIComponent(doctorId)}`, "POST", {}, true);
	    			if (response.ok) {
		    			showToast("Failed to grant access to doctor.", "error");
				    } else {
                        showToast("Appointment booked and doctor access granted.", "success");
			    		document.getElementById("appointmentSuccess").style.display = "block";
				    	form.reset();
		            }
			    } catch (error) {
				    console.error("Error granting permission:", error);
				    showToast("An error occurred while granting access.", "error");
		    	}
	    	});
		}, 0);
		break;

        case "consultation":
            sectionContent = `
                <h2>Consultation</h2>
                <div class="section-grid">
                    <div class="section-card">
                        <h3><i class="fas fa-search"></i> Search Patient Records</h3>
                        <div style="margin-bottom: 15px;">
                            <label>Patient ID</label>
                            <input type="text" id="PatientId" placeholder="Enter Patient ID" style="width: 100%;">
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label>File ID (Optional)</label>
                            <input type="text" id="FileId" placeholder="Enter File ID" style="width: 100%;">
                        </div>
                        <button onclick="searchRecords()" style="width: 100%;">Search Records</button>
                    </div>
                    <div class="section-card">
                        <h3><i class="fas fa-file-medical"></i> Patient Records</h3>
                        <div id="consultationResults" class="file-preview">
                            <!-- Results will be displayed here -->
                        </div>
                    </div>
                </div>
            `;
            break;    
        case "retrieve-records":
            sectionContent = `
                <h2>Retrieve Medical Records</h2>
                <div class="section-grid">
                    <div class="section-card">
                        <h3><i class="fas fa-search"></i> Search Records</h3>
                        <div style="margin-bottom: 15px;">
                            <label>File ID</label>
                            <input type="text" id="FileId" placeholder="Enter File ID" style="width: 100%;">
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label>Patient ID</label>
                            <input type="text" id="PatientId" placeholder="Enter Patient ID" style="width: 100%;">
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label>File Type</label>
                            <select id="fileTypeSearch" style="width: 100%;">
                                <option value="all">All Types</option>
                                <option value="pdf">PDF Document</option>
                                <option value="xml">XML File</option>
                                <option value="json">JSON File</option>
                                <option value="csv">CSV File</option>
                                <option value="jpg">JPG Image</option>
                            </select>
                        </div>
                        <button onclick="searchRecords()" style="width: 100%;">Search Records</button>
                    </div>
                    <div class="section-card">
                        <h3><i class="fas fa-file-medical"></i> Search Results</h3>
                        <div id="searchResults" class="file-preview">
                            <!-- Results will be displayed here -->
                        </div>
                    </div>
                </div>
            `;
            break;
            
        case "find-patient-file":
            sectionContent = `
                <h2>Find Patient File</h2>
                <div class="section-grid">
                    <div class="section-card">
                        <h3><i class="fas fa-search"></i> Search Files</h3>
                        <div style="margin-bottom: 15px;">
                            <label>Patient ID</label>
                            <input type="text" id="searchPatientId" placeholder="Enter Patient ID" style="width: 100%;">
                        </div>
                        <div style="margin-bottom: 15px;">
                            <label>File ID (Optional)</label>
                            <input type="text" id="searchFileId" placeholder="Enter File ID" style="width: 100%;">
                        </div>
                        <button onclick="searchPatientFiles()" style="width: 100%;">Search Files</button>
                    </div>
                    <div class="section-card">
                        <h3><i class="fas fa-file-medical"></i> Search Results</h3>
                        <div id="fileSearchResults" class="file-preview">
                            <!-- Results will be displayed here -->
                        </div>
                    </div>
                </div>
            `;
            break;
            
        default:
            sectionContent = `
                <h2>${sectionTitles[sectionId] || sectionId.replace('-', ' ')}</h2>
                <div class="section-content">
                    <p>This would display ${role}'s ${sectionTitles[sectionId] || sectionId.replace('-', ' ')} content.</p>
                </div>
            `;
    }
    
    content.innerHTML = sectionContent;
}

function generateRecentPatientRows() {
    // Sort patients by last visit date (most recent first)
    const recentPatients = [...patients].sort((a, b) => {
        return new Date(b.lastVisit || '2000-01-01') - new Date(a.lastVisit || '2000-01-01');
    }).slice(0, 10); // Show only the 10 most recent patients

    return recentPatients.map(patient => `
        <tr>
            <td>${patient.id}</td>
            <td>${patient.firstName} ${patient.lastName}</td>
            <td>${formatDate(patient.lastVisit || '')}</td>
            <td><span class="status-badge ${patient.status === 'Active' ? 'status-active' : 'status-discharged'}">${patient.status}</span></td>
            <td>
                <button class="small-btn" onclick="viewPatientRecords('${patient.id}')">View Records</button>
            </td>
        </tr>
    `).join('');
}

function generatePatientOptions() {
    return patients.map(patient => `
        <option value="${patient.id}">${patient.firstName} ${patient.lastName} (${patient.id})</option>
    `).join('');
}

function logout() {
    localStorage.removeItem("userRole");
    localStorage.removeItem("token");
    location.reload();
}

function toggleSidebar() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    sidebar.classList.toggle("open");
    overlay.classList.toggle("active");
}

// Initialize the application
window.onload = function () {
    let role = localStorage.getItem("userRole");
    if (role) {
        document.getElementById("loginContainer").style.display = "none";
        document.getElementById("dashboard").style.display = "flex";
        loadDashboard(role);
    }
    document.getElementById('patientForm').addEventListener('submit', addPatient);
    document.getElementById('recordsForm').addEventListener('submit', requestRecords);
};

async function addPatient(event) {
    event.preventDefault();
    const patientId = document.getElementById('simplePatientId').value.trim();
    
    if (!patientId) {
        showAlert('Please enter a valid patient ID', 'error', 'patientAlert');
        return;
    }

    try {
        const response = await makeApiRequest('/patient/', 'POST', {
            patient_id: patientId
        });
        
        showAlert('Patient added successfully!', 'success', 'patientAlert');
        closeModal();
        // Refresh patient list if on patient management page
        if (document.getElementById('patientTableBody')) {
            loadPatients();
        }
    } catch (error) {
        showAlert(error.message, 'error', 'patientAlert');
    }
}

async function requestRecords(event) {
    event.preventDefault();
    const hospital = document.getElementById('requestHospital').value;
    const fromDate = document.getElementById('fromDate').value;
    const toDate = document.getElementById('toDate').value;
    const recordTypes = Array.from(document.querySelectorAll('input[name="recordType"]:checked'))
        .map(checkbox => checkbox.value);
    const deliveryMethod = document.getElementById('deliveryMethod').value;
    const notes = document.getElementById('requestNotes').value;

    if (!fromDate || !toDate) {
        showAlert('Please select a valid date range', 'error', 'recordsAlert');
        return;
    }

    if (recordTypes.length === 0) {
        showAlert('Please select at least one record type', 'error', 'recordsAlert');
        return;
    }

    try {
        const response = await makeApiRequest('/request-records/', 'POST', {
            hospital,
            from_date: fromDate,
            to_date: toDate,
            record_types: recordTypes,
            delivery_method: deliveryMethod,
            notes
        });
        
        showAlert('Record request submitted successfully!', 'success', 'recordsAlert');
        closeModal();
    } catch (error) {
        showAlert(error.message, 'error', 'recordsAlert');
    }
}

function showAlert(message, type, containerId) {
    const alertContainer = document.getElementById(containerId);
    alertContainer.textContent = message;
    alertContainer.className = `alert alert-${type}`;
    alertContainer.style.display = 'block';
}

function closeModal() {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.style.display = 'none';
    });
}

async function loadPatients() {
    try {
        const response = await makeApiRequest('/patients/', 'GET');
        const patients = response.data || [];
        const tableBody = document.getElementById('patientTableBody');
        
        if (tableBody) {
            tableBody.innerHTML = patients.map(patient => `
                <tr>
                    <td>${patient.patient_id}</td>
                    <td>${patient.name || 'N/A'}</td>
                    <td>${formatDate(patient.last_visit)}</td>
                    <td><span class="status-badge ${patient.status === 'Active' ? 'status-active' : 'status-discharged'}">${patient.status}</span></td>
                    <td>
                        <button class="small-btn" onclick="viewPatientRecords('${patient.patient_id}')">View Records</button>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading patients:', error);
        showToast('Failed to load patients', 'error');
    }
}

async function searchRecords() {
    try {
	const patientId = document.getElementById("PatientId").value.trim();
	const fileId = document.getElementById("FileId").value.trim();
	let body={};
	if(patientId){
		console.log("at patient_id:", patientId);
		body.patient_id=patientId;
	}
	else if(fileId){
		console.log("at file_id:", fileId);
		body.file_id=fileId;
	}
	else{
		console.log("at else: fetching all");

	}
	const response= await makeApiRequest('/file/','POST',body);
        const records = response.data || [];
        
        // Show records in a modal or update the content section
        const content = document.getElementById('contentSection');
        content.innerHTML = `
            <h2>Patient Records</h2>
            <div class="section-grid">
                ${records.map(record => `
                    <div class="record-item">
                        <div class="record-header">
                            <span class="record-title">${record.file_type}</span>
                            <span class="record-date">${formatDate(record.upload_date)}</span>
                        </div>
                        <div class="record-details">
                            <p>File ID: ${record.file_id}</p>
                            <p>Status: ${record.status}</p>
                        </div>
                        <div class="record-actions">
                            <button class="small-btn" onclick='downloadFile(${JSON.stringify(record)})'>Download</button>
                            <button class="small-btn" onclick='viewFile(${JSON.stringify(record)})'>View</button>
                            <select id="format-${record.file_id}" class="small-select">
                                   <option value="pdf">PDF</option>
                                   <option value="txt">TXT</option>
                                   <option value="docx">DOCX</option>
                                   <option value="json">JSON</option>
                            </select>
                            <button class="small-btn" onclick='convertFile(${JSON.stringify(record)},"format-${record.file_id}")'>Convert</button>

                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } catch (error) {
        console.error('Error loading patient records:', error);
        showToast('Failed to load patient records', 'error');
    }
}

async function downloadFile(record) {
    try {
	let body={};
	
	const payload={
		message: "",
		data: [record]
	};
        const blob = await makeApiRequest(`/file/download/`, 'POST',payload,true);
        // Handle file download;
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `file_${record.file_id}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        console.error('Error downloading file:', error);
        showToast('Failed to download file', 'error');
    }
}

async function viewFile(record) {
    try {
        console.log(record);
	console.log("requesting api for view file http url");
	const payload={
		message: "",
		data: [record]
	};
        const blob = await makeApiRequest(`/file/view/`, 'POST',payload,true);
	console.log("responce received ")
        // Handle file viewing
	console.log("created blob and trying to create url");
        const url = window.URL.createObjectURL(blob);
	console.log("url created and tryiny to open new window");
        window.open(url, '_blank');
    } catch (error) {
        console.error('Error viewing file:', error);
        showToast('Failed to view file', 'error');
    }
}

async function convertFile(record, selectId) {
	try{
		console.log(record);
		console.log(selectId);
		const target_format = "."+document.getElementById(selectId).value.trim();
		console.log(target_format);
		const payload={
			message:"",
			data:[record] 
		};
		const response = await makeApiRequest(`/convert/?requested_format=${encodeURIComponent(target_format)}`, 'POST',payload,true);
		console.log(response);
		if(response.ok){
			showToast('Conversion started!', 'success');
		}
	} catch (error) {
		console.error('Error viewing file:', error);
        	showToast('Failed to view file', 'error');
	}
}
		
// Registration Modal Functions
function showRegisterModal() {
    document.getElementById('registerModal').style.display = 'block';
}

function closeRegisterModal() {
    document.getElementById('registerModal').style.display = 'none';
    document.getElementById('registerAlert').style.display = 'none';
    document.getElementById('registerForm').reset();
}

async function register(event) {
    event.preventDefault();
    
    const role = document.getElementById('registerRole').value;
    const username = document.getElementById('registerUsername').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                role,
                username,
                email,
                password
            })
        });

        const data = await response.json();
        const alertElement = document.getElementById('registerAlert');
        
        if (response.ok) {
            alertElement.textContent = 'Registration successful! You can now login.';
            alertElement.className = 'alert success';
            alertElement.style.display = 'block';
            
            // Close registration modal after 2 seconds
            setTimeout(() => {
                closeRegisterModal();
            }, 2000);
        } else {
            alertElement.textContent = data.message || 'Registration failed. Please try again.';
            alertElement.className = 'alert error';
            alertElement.style.display = 'block';
        }
    } catch (error) {
        const alertElement = document.getElementById('registerAlert');
        alertElement.textContent = 'An error occurred. Please try again.';
        alertElement.className = 'alert error';
        alertElement.style.display = 'block';
    }
} 

function connectWebSocket(token) {
	const wsUrl = `ws://localhost:8000/ws/notifications?token=${encodeURIComponent(token)}`;
	const socket = new WebSocket(wsUrl);
	socket.onopen = () => {
    		console.log("✅ WebSocket connection established");
	};
	socket.onmessage = (event) => {
	    try {
        	const data = JSON.parse(event.data);
        	console.log("🔔 Notification received:", data);

        	// Customize the display logic
        	showToast(`📢 ${data.event || "Notification received"}`, 'info');
    	} catch (err) {
        	console.error("❌ Failed to parse WebSocket message:", err);
    	}
	};

	socket.onclose = (event) => {
    		console.warn("⚠️ WebSocket closed:", event.reason);
    		showToast("📴 WebSocket disconnected", 'warning');
	};

	socket.onerror = (error) => {
    		console.error("WebSocket error:", error);
	};
}
