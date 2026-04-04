class downloadarr {
    constructor() {
        this.baseURL = window.location.origin;
        this.init();
    }


    init() {
        this.eventListeners();
    }

    eventListeners() {
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                const tab = e.target.dataset.tab;
                this.switchTab(tab);
            })
        });

        // search metadata wld be like ios app
        document.getElementById('searchBtn').addEventListener('click', () => this.searchMetadata());

        document.getElementById('searchQuery').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.searchMetadata();
        });

        document.getElementById('refresh').addEventListener('click', () => this.loadlibrary());
        setInterval(() => this.checkdnwld(), 3000);
    }

    switchTab(tab) {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
        document.getElementById(tab).classList.add('active');
        
        if (tab == 'library') this.loadlibrary();
    }

    showLoading(show= true) {
        document.getElementById('loadingOverlay').classList.toggle('active', show);
    }
    
    // functions
    showToast(message) {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.classList.add('active');
        setTimeout(() => toast.classList.remove('active'), 3000);
    }

    async apiCall(endpoint, method = 'GET', body=null) {
        try {
            const options = {
                method,
                headers: { 'Content-Type': 'application/json'},
            };
            if (body) options.body = JSON.stringify(body);

            const response = await fetch(`${this.baseURL}${endpoint}`, options)

            if (!response.ok) throw new Error(`api error: ${response}`); 
            return await response.json();
        } catch (error) {
            this.showToast(error.message);
            throw error
        }
    }

    //metdataaaaa
    async searchMetadata() {
        const query = document.getElementById('searchQuery').value.trim();
        if (!query) {
            this.showToast('enter a search query')
            return;
        }

        this.showLoading();
        try {
            const response = await this.apiCall('/search/metadata', 'POST', { query });
            this.displayResults(response.results || []);
        } catch (error) {
            console.error(error);
        } finally {
            this.showLoading(false);
        }
    }


    displayResults(results) {
        const container = document.getElementById('metadataResults');
        const noResults = document.getElementById('noResults');

        if (results.length === 0) {
            container.innerHTML = '';
            noResults.style.display = 'block';
            return;
        }

        noResults.style.display = 'none';
        container.innerHTML = results.map(r => `
            <div class="card" onclick="app.selectMetadata(${JSON.stringify(r).replace(/"/g, '&quot;')})">
                <div class="card-image">
                    ${r.albumArtURL ? `<img src="${r.albumArtURL}" alt="${r.title}">`: 'Music'}
                </div>
                <div class="card-content">
                    <div class="card-title">${this.escape(r.title)}</div>
                    <div class="card-meta">
                        ${this.escape(r.artist)}
                        <div class="card-meta-small">${this.escape(r.album)}</div>
                    </div>
                    <button class="card-action">Select</button>
                </div>
            </div>
        `).join('');
    }

    async selectMetadata(metadata) {
        this.showLoading();
        try {
            const response = await this.apiCall('/search/youtube', 'POST', {
                query: `${metadata.artist} - ${metadata.title}`
            })
            this.showDetail(metadata, response.results || []);
        } catch (error) {
            console.error(error);
        } finally {
            this.showLoading(false);
        }
    }

    showDetail(metadata, videos) {
        const modal = document.getElementById('modal');
        const body = document.getElementById('modalBody');

        body.innerHTML = `
            <div class="modal-header">
                ${metadata.albumArtURL ? `<img src="${metadata.albumArtURL}" alt="${metadata.title}">` : ''}
                <h2>${this.escape(metadata.title)}</h2>
                <p>${this.escape(metadata.artist)}</p>
                <small>${this.escape(metadata.album)} • ${metadata.date || 'no date'}</small>
            </div>

            <div class="modal-section">
                <h3>youtube sources</h3>
                ${videos.map(v => `
                    <div class="youtube-item">
                        <div class="youtube-title">${this.escape(v.title)}</div>
                        <div class="youtube-channel">${this.escape(v.channelName || 'Unknown')}</div>
                        <button class="youtube-download" onclick="app.startDownload('${v.url.replace(/'/g, "\\'")}', ${JSON.stringify(metadata).replace(/"/g, '&quot;')})">
                            download
                        </button>
                    </div>
                `).join('')}
            </div>
        `;

        modal.classList.add('active');
    }

    closeModal() {
        document.getElementById('modal').classList.remove('active');
    }

    async startDownload(url, metadata) {
        this.showLoading();
        try {
            await this.apiCall('/download', 'POST', { url, metadata });
            this.showToast('download started!');
            this.closeModal();
        } catch (error) {
            console.error(error);
        } finally {
            this.showLoading(false);
        }
    }

    checkdnwld() {
        // dnwliad monitoring, might just put logs here though
    }

    async loadlibrary() {
        this.showLoading();
        try {
            const response = await this.apiCall('/library');
            this.displayLibrary(response.songs || []);
        } catch (error) {
            console.error(error);
        } finally {
            this.showLoading(false);
        }
    }
    
    displayLibrary(songs) {
        const container = document.getElementById('libraryList');
        const noLibrary = document.getElementById('noLibrary');

        if (songs.length === 0) {
            container.innerHTML = '';
            noLibrary.style.display = 'block'
            return;
        }

        noLibrary.style.display = 'none';
        container.innerHTML = songs.map(s => `
            <div class="card">
                <div class="card-image">🎵</div>
                <div class="card-content">
                    <div class="card-title">${this.escape(s.filename)}</div>
                    <div class="card-meta">
                        ${this.escape(s.artist)}
                        <div class="card-meta-small">${this.escape(s.album)}</div>
                    </div>
                    <button class="card-action" onclick="window.open('${s.url}')">download</button>
                </div>
            </div>
        `).join('');
    }

    escape(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}

const app = new downloadarr();
