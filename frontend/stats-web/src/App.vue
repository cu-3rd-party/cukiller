<script setup>
import { onMounted, ref } from 'vue'

const ratingLimit = ref(10)
const ratingOffset = ref(0)
const ratingItems = ref([])
const ratingLoading = ref(false)
const ratingError = ref('')

const killsLimit = ref(10)
const killsOffset = ref(0)
const killsItems = ref([])
const killsLoading = ref(false)
const killsError = ref('')

const totalStatus = ref('confirmed')
const totalValue = ref(null)
const totalLoading = ref(false)
const totalError = ref('')

const userName = ref('')
const userStats = ref(null)
const userLoading = ref(false)
const userError = ref('')

const backendUrl = getBackendUrl()

function getBackendUrl() {
  const runtimeValue = window.RUNTIME_CONFIG?.BACKEND_URL
  if (runtimeValue !== undefined && runtimeValue !== '__BACKEND_URL__') {
    return runtimeValue.replace(/\/$/, '')
  }
  const buildValue = import.meta.env.VITE_BACKEND_URL
  if (buildValue) {
    return buildValue.replace(/\/$/, '')
  }
  return ''
}

function buildUrl(path, params) {
  const raw = backendUrl ? `${backendUrl}${path}` : path
  const url = new URL(raw, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        url.searchParams.set(key, String(value))
      }
    })
  }
  return url.toString()
}

async function fetchJson(path, params) {
  const response = await fetch(buildUrl(path, params))
  const text = await response.text()
  if (!response.ok) {
    throw new Error(text || response.statusText)
  }
  if (!text) {
    return null
  }
  try {
    return JSON.parse(text)
  } catch (error) {
    throw new Error('failed to parse response')
  }
}

function formatName(entry) {
  const parts = [entry.given_name, entry.family_name].filter(Boolean)
  return parts.join(' ').trim()
}

async function loadRating() {
  ratingLoading.value = true
  ratingError.value = ''
  try {
    const data = await fetchJson('/api/stats/rating', {
      limit: ratingLimit.value,
      offset: ratingOffset.value,
    })
    ratingItems.value = data?.items || []
  } catch (error) {
    ratingError.value = error.message || 'failed to load rating'
    ratingItems.value = []
  } finally {
    ratingLoading.value = false
  }
}

async function loadKills() {
  killsLoading.value = true
  killsError.value = ''
  try {
    const data = await fetchJson('/api/stats/kills', {
      limit: killsLimit.value,
      offset: killsOffset.value,
    })
    killsItems.value = data?.items || []
  } catch (error) {
    killsError.value = error.message || 'failed to load kills'
    killsItems.value = []
  } finally {
    killsLoading.value = false
  }
}

async function loadTotal() {
  totalLoading.value = true
  totalError.value = ''
  try {
    const data = await fetchJson('/api/stats/total', { status: totalStatus.value })
    totalValue.value = data?.total ?? null
  } catch (error) {
    totalError.value = error.message || 'failed to load total'
    totalValue.value = null
  } finally {
    totalLoading.value = false
  }
}

async function loadUser() {
  userLoading.value = true
  userError.value = ''
  try {
    const data = await fetchJson('/api/stats', { user: userName.value })
    userStats.value = data
  } catch (error) {
    userError.value = error.message || 'failed to load user stats'
    userStats.value = null
  } finally {
    userLoading.value = false
  }
}

onMounted(() => {
  loadRating()
  loadKills()
  loadTotal()
})
</script>

<template>
  <main>
    <h1>Game stats</h1>
    <p>Backend: {{ backendUrl || 'same origin' }}</p>

    <nav>
      <a href="#rating">Rating leaderboard</a>
      <a href="#kills">Kills leaderboard</a>
      <a href="#total">Kill totals</a>
      <a href="#user">User stats</a>
    </nav>

    <div class="panel-grid">
      <section id="rating">
        <h2>Rating leaderboard</h2>
        <form @submit.prevent="loadRating">
          <label>
            Limit
            <input v-model.number="ratingLimit" type="number" min="1" max="100" />
          </label>
          <label>
            Offset
            <input v-model.number="ratingOffset" type="number" min="0" />
          </label>
          <button type="submit">Load</button>
        </form>
        <p v-if="ratingLoading">Loading...</p>
        <p v-else-if="ratingError">{{ ratingError }}</p>
        <table v-else-if="ratingItems.length">
          <thead>
            <tr>
              <th>#</th>
              <th>TG ID</th>
              <th>Name</th>
              <th>Username</th>
              <th>Rating</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(entry, index) in ratingItems" :key="entry.tg_id">
              <td>{{ index + 1 + ratingOffset }}</td>
              <td>{{ entry.tg_id }}</td>
              <td>{{ formatName(entry) }}</td>
              <td>{{ entry.username }}</td>
              <td>{{ entry.rating }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else>No data.</p>
      </section>

      <section id="kills">
        <h2>Kills leaderboard</h2>
        <form @submit.prevent="loadKills">
          <label>
            Limit
            <input v-model.number="killsLimit" type="number" min="1" max="100" />
          </label>
          <label>
            Offset
            <input v-model.number="killsOffset" type="number" min="0" />
          </label>
          <button type="submit">Load</button>
        </form>
        <p v-if="killsLoading">Loading...</p>
        <p v-else-if="killsError">{{ killsError }}</p>
        <table v-else-if="killsItems.length">
          <thead>
            <tr>
              <th>#</th>
              <th>TG ID</th>
              <th>Name</th>
              <th>Username</th>
              <th>Kills</th>
              <th>Rating</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(entry, index) in killsItems" :key="entry.tg_id">
              <td>{{ index + 1 + killsOffset }}</td>
              <td>{{ entry.tg_id }}</td>
              <td>{{ formatName(entry) }}</td>
              <td>{{ entry.username }}</td>
              <td>{{ entry.kills }}</td>
              <td>{{ entry.rating }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else>No data.</p>
      </section>

      <section id="total">
        <h2>Kill totals</h2>
        <form @submit.prevent="loadTotal">
          <label>
            Status
            <select v-model="totalStatus">
              <option value="pending">pending</option>
              <option value="confirmed">confirmed</option>
              <option value="rejected">rejected</option>
              <option value="canceled">canceled</option>
              <option value="timeout">timeout</option>
            </select>
          </label>
          <button type="submit">Load</button>
        </form>
        <p v-if="totalLoading">Loading...</p>
        <p v-else-if="totalError">{{ totalError }}</p>
        <p v-else-if="totalValue !== null">Total: {{ totalValue }}</p>
        <p v-else>No data.</p>
      </section>

      <section id="user">
        <h2>User stats</h2>
        <form @submit.prevent="loadUser">
          <label>
            Username
            <input v-model.trim="userName" type="text" placeholder="igamamaev" />
          </label>
          <button type="submit">Load</button>
        </form>
        <p v-if="userLoading">Loading...</p>
        <p v-else-if="userError">{{ userError }}</p>
        <table v-else-if="userStats">
          <thead>
            <tr>
              <th>TG ID</th>
              <th>Name</th>
              <th>Username</th>
              <th>Rating</th>
              <th>Kills</th>
              <th>Deaths</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{{ userStats.tg_id }}</td>
              <td>{{ formatName(userStats) }}</td>
              <td>{{ userStats.username }}</td>
              <td>{{ userStats.rating }}</td>
              <td>{{ userStats.kills }}</td>
              <td>{{ userStats.deaths }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else>No data.</p>
      </section>
    </div>
  </main>
</template>
