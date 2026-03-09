/**
 * companion-app/src/screens/ActionMappingScreen.js
 *
 * Shows all labels the user has taught the AI and their mapped text actions.
 * Users can see, read current mappings, and the Pi URL can be updated from here.
 */

import React, { useState, useCallback } from 'react';
import {
    View, Text, StyleSheet, FlatList, TouchableOpacity,
    ActivityIndicator, RefreshControl, TextInput,
    Animated, Alert, ScrollView,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { getActionMappings } from '../services/api';

const COLORS = {
    bg: '#0A0F1E',
    card: '#111827',
    border: '#1F2937',
    primary: '#3B82F6',
    success: '#10B981',
    text: '#F9FAFB',
    muted: '#6B7280',
    yellow: '#FBBF24',
};

export default function ActionMappingScreen() {
    const [mappings, setMappings] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refresh, setRefresh] = useState(false);
    const [error, setError] = useState(null);
    const [search, setSearch] = useState('');

    const loadMappings = async (isRefresh = false) => {
        if (isRefresh) setRefresh(true);
        else setLoading(true);
        setError(null);
        try {
            const res = await getActionMappings();
            setMappings(res.data.mappings ?? []);
        } catch (e) {
            setError('Could not reach the Raspberry Pi.\nCheck the IP in src/services/api.js.');
        } finally {
            setLoading(false);
            setRefresh(false);
        }
    };

    useFocusEffect(useCallback(() => { loadMappings(); }, []));

    const filtered = search.trim()
        ? mappings.filter(m =>
            m.label.toLowerCase().includes(search.toLowerCase()) ||
            (m.action ?? '').toLowerCase().includes(search.toLowerCase())
        )
        : mappings;

    const renderItem = ({ item }) => (
        <View style={styles.card}>
            <View style={styles.cardRow}>
                <View style={[styles.dot, { backgroundColor: item.has_action ? COLORS.success : COLORS.muted }]} />
                <View style={styles.cardContent}>
                    <Text style={styles.labelText}>{item.label}</Text>
                    {item.has_action ? (
                        <View style={styles.actionBadge}>
                            <Text style={styles.actionIcon}>⚡</Text>
                            <Text style={styles.actionText}>{item.action}</Text>
                        </View>
                    ) : (
                        <Text style={styles.noAction}>No action mapped</Text>
                    )}
                </View>
            </View>
        </View>
    );

    return (
        <View style={styles.container}>
            {/* Search bar */}
            <View style={styles.searchRow}>
                <TextInput
                    style={styles.searchInput}
                    value={search}
                    onChangeText={setSearch}
                    placeholder="Search labels or actions…"
                    placeholderTextColor={COLORS.muted}
                />
                {search.length > 0 && (
                    <TouchableOpacity onPress={() => setSearch('')} style={styles.clearBtn}>
                        <Text style={{ color: COLORS.muted }}>✕</Text>
                    </TouchableOpacity>
                )}
            </View>

            {loading ? (
                <View style={styles.center}>
                    <ActivityIndicator size="large" color={COLORS.primary} />
                    <Text style={[styles.muted, { marginTop: 12 }]}>Connecting to Pi…</Text>
                </View>
            ) : error ? (
                <View style={styles.center}>
                    <Text style={styles.errorText}>{error}</Text>
                    <TouchableOpacity onPress={() => loadMappings()} style={styles.retryBtn}>
                        <Text style={styles.retryText}>Retry</Text>
                    </TouchableOpacity>
                </View>
            ) : filtered.length === 0 ? (
                <View style={styles.center}>
                    <Text style={styles.emptyIcon}>🤖</Text>
                    <Text style={styles.muted}>
                        {search ? 'No matches found' : 'No labels taught yet.\nUse the Raspberry Pi in Learn Mode to teach the AI.'}
                    </Text>
                </View>
            ) : (
                <FlatList
                    data={filtered}
                    keyExtractor={item => item.label}
                    renderItem={renderItem}
                    contentContainerStyle={styles.list}
                    refreshControl={
                        <RefreshControl
                            refreshing={refresh}
                            onRefresh={() => loadMappings(true)}
                            tintColor={COLORS.primary}
                        />
                    }
                    ListHeaderComponent={
                        <Text style={styles.countText}>
                            {filtered.length} label{filtered.length !== 1 ? 's' : ''}
                            {' • '}
                            {filtered.filter(m => m.has_action).length} with action
                        </Text>
                    }
                />
            )}
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: COLORS.bg },
    center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
    list: { paddingHorizontal: 16, paddingBottom: 24 },
    countText: { fontSize: 11, color: COLORS.muted, marginVertical: 12, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.8 },
    searchRow: { flexDirection: 'row', margin: 16, backgroundColor: COLORS.card, borderRadius: 12, borderWidth: 1, borderColor: COLORS.border, alignItems: 'center', paddingHorizontal: 14 },
    searchInput: { flex: 1, color: COLORS.text, fontSize: 14, paddingVertical: 12 },
    clearBtn: { padding: 4 },
    card: { backgroundColor: COLORS.card, borderRadius: 14, borderWidth: 1, borderColor: COLORS.border, marginBottom: 10, padding: 14 },
    cardRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 12 },
    dot: { width: 8, height: 8, borderRadius: 4, marginTop: 6 },
    cardContent: { flex: 1 },
    labelText: { fontSize: 16, fontWeight: '800', color: COLORS.text, textTransform: 'capitalize', marginBottom: 4 },
    actionBadge: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#1D4ED820', borderRadius: 8, paddingHorizontal: 8, paddingVertical: 4, gap: 6, alignSelf: 'flex-start' },
    actionIcon: { fontSize: 12 },
    actionText: { fontSize: 13, color: COLORS.primary, fontWeight: '600', flexShrink: 1 },
    noAction: { fontSize: 12, color: COLORS.muted, fontStyle: 'italic' },
    muted: { color: COLORS.muted, textAlign: 'center', lineHeight: 22, fontSize: 14 },
    emptyIcon: { fontSize: 48, marginBottom: 12 },
    errorText: { color: '#F87171', textAlign: 'center', lineHeight: 22, marginBottom: 16, fontSize: 14 },
    retryBtn: { backgroundColor: COLORS.primary, paddingHorizontal: 24, paddingVertical: 10, borderRadius: 10 },
    retryText: { color: '#fff', fontWeight: '700', fontSize: 14 },
});
