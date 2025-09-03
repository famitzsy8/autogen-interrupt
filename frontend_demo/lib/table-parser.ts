/**
 * Robust table parser for orchestrator's final investigation output
 * Handles messy markdown tables and extracts congress member data
 */

export interface CongressMember {
  name: string; // Clean name without party
  chamber: string; // Representative or Senator
  party?: string; // Extracted from name if available (D, R, I)
  state: string; // State code (e.g., "MD", "TN")
  district?: string; // District number for House members (e.g., "03")
  rank: number;
  reason: string;
}

export interface ParsedTable {
  members: CongressMember[];
  totalMembers: number;
  investigationComplete: boolean;
  billId?: string;
  // New dual table support
  hasDualTables?: boolean;
  alignedMembers?: CongressMember[];
  opposedMembers?: CongressMember[];
}

class TableParser {
  
  /**
   * Parse the final orchestrator message and extract congress member table(s)
   * Now supports dual tables (aligned vs opposed politicians)
   */
  public parseOrchestratorTable(messageContent: string): ParsedTable | null {
    try {
      // Check for dual tables first
      const hasDualTables = this.detectDualTables(messageContent);
      
      if (hasDualTables) {
        return this.parseDualTables(messageContent);
      }

      // Fallback to single table parsing
      return this.parseSingleTable(messageContent);

    } catch (error) {
      console.error('Error parsing orchestrator table:', error);
      return null;
    }
  }

  private detectDualTables(content: string): boolean {
    // Count actual table headers (not just separators)
    const lines = content.split('\n');
    let tableHeaderCount = 0;
    
    for (const line of lines) {
      const lineLower = line.toLowerCase().trim();
      // Look for markdown table headers with the expected columns
      if (line.includes('|') && 
          lineLower.includes('congress member') && 
          (lineLower.includes('chamber') || lineLower.includes('party')) &&
          lineLower.includes('involvement rank')) {
        tableHeaderCount++;
      }
    }
    
    console.log(`🔍 Dual table detection: found ${tableHeaderCount} table headers`);
    
    // Simple requirement: exactly 2 table headers
    return tableHeaderCount === 2;
  }

  private parseDualTables(messageContent: string): ParsedTable | null {
    try {
      // Extract tables by order: 1st = aligned, 2nd = opposed
      const alignedSection = this.extractTableByOrder(messageContent, 1); // First table
      const alignedMembers = alignedSection ? this.parseTableRows(alignedSection) : [];

      const opposedSection = this.extractTableByOrder(messageContent, 2); // Second table
      const opposedMembers = opposedSection ? this.parseTableRows(opposedSection) : [];

      console.log(`✅ Parsed ${alignedMembers.length} aligned members, ${opposedMembers.length} opposed members`);

      // Combine all members for legacy compatibility
      const allMembers = [...alignedMembers, ...opposedMembers];

      if (allMembers.length === 0) {
        return null;
      }

      // Extract bill ID if available
      const billId = this.extractBillId(messageContent);

      return {
        members: allMembers,
        totalMembers: allMembers.length,
        investigationComplete: this.isInvestigationComplete(messageContent),
        billId,
        hasDualTables: true,
        alignedMembers,
        opposedMembers
      };

    } catch (error) {
      console.error('Error parsing dual tables:', error);
      return null;
    }
  }

  private parseSingleTable(messageContent: string): ParsedTable | null {
    try {
      // Look for table indicators
      const hasTable = this.detectTableInMessage(messageContent);
      if (!hasTable) {
        return null;
      }

      // Extract the table section
      const tableSection = this.extractTableSection(messageContent);
      if (!tableSection) {
        return null;
      }

      // Parse table rows
      const members = this.parseTableRows(tableSection);
      if (members.length === 0) {
        return null;
      }

      // Extract bill ID if available
      const billId = this.extractBillId(messageContent);

      return {
        members,
        totalMembers: members.length,
        investigationComplete: this.isInvestigationComplete(messageContent),
        billId,
        hasDualTables: false
      };

    } catch (error) {
      console.error('Error parsing single table:', error);
      return null;
    }
  }

  private extractTableByOrder(content: string, tableNumber: number): string | null {
    const lines = content.split('\n');
    const tablesFound: string[] = [];
    let currentTableLines: string[] = [];
    let inTable = false;
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const lineLower = line.toLowerCase().trim();
      
      // Look for table headers
      if (line.includes('|') && 
          lineLower.includes('congress member') && 
          (lineLower.includes('chamber') || lineLower.includes('party')) &&
          lineLower.includes('involvement rank')) {
        
        // If we were already in a table, save the previous one
        if (inTable && currentTableLines.length > 0) {
          tablesFound.push(currentTableLines.join('\n'));
          currentTableLines = [];
        }
        
        // Start new table
        inTable = true;
        currentTableLines.push(line);
        console.log(`📊 Found table #${tablesFound.length + 1} header at line ${i}: ${line.trim()}`);
        continue;
      }
      
      // Collect table content if we're in a table
      if (inTable) {
        // Include separator lines and data rows
        if (line.includes('|')) {
          // Check if this is a separator line
          if (line.trim().replace(/\|/g, '').replace(/[-:]/g, '').trim() === '') {
            currentTableLines.push(line); // Separator line
            continue;
          }
          
          // Check if this is a data row (has enough columns)
          if (line.split('|').length >= 5) { // At least 5 columns expected
            currentTableLines.push(line);
            continue;
          }
        }
        
        // Stop conditions for current table
        // 1. Empty line after table content
        if (line.trim() === '' && currentTableLines.length > 2) {
          tablesFound.push(currentTableLines.join('\n'));
          currentTableLines = [];
          inTable = false;
          continue;
        }
        
        // 2. Non-table line after table started
        if (!line.includes('|') && currentTableLines.length > 2) {
          console.log(`🛑 Table #${tablesFound.length + 1} ended at line ${i}: ${line.trim()}`);
          tablesFound.push(currentTableLines.join('\n'));
          currentTableLines = [];
          inTable = false;
        }
      }
    }
    
    // Don't forget the last table if we ended while in one
    if (inTable && currentTableLines.length > 0) {
      tablesFound.push(currentTableLines.join('\n'));
    }
    
    console.log(`📋 Found ${tablesFound.length} total tables`);
    
    // Return the requested table (1-indexed)
    if (tableNumber <= tablesFound.length) {
      const result = tablesFound[tableNumber - 1];
      console.log(`✅ Returning table #${tableNumber} with ${result.split('\n').length} lines`);
      return result;
    } else {
      console.log(`❌ Table #${tableNumber} not found, only have ${tablesFound.length} tables`);
      return null;
    }
  }

  private detectTableInMessage(content: string): boolean {
    const tableIndicators = [
      'Congress Member',
      'Chamber',
      'State/District',
      'Involvement Rank',
      'Reason',
      '|---|',
      'TERMINATE',
      'investigation complete',
      'table delivered'
    ];

    const contentLower = content.toLowerCase();
    const indicatorMatches = tableIndicators.filter(indicator => 
      contentLower.includes(indicator.toLowerCase())
    );

    return indicatorMatches.length >= 3; // Need at least 3 indicators for confidence
  }

  private extractTableSection(content: string): string | null {
    // Find table boundaries - look for markdown table structure
    const lines = content.split('\n');
    let tableStart = -1;
    let tableEnd = -1;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      
      // Look for table header line with |
      if (line.includes('Congress Member') && line.includes('|')) {
        tableStart = i;
      }
      
      // Look for separator line with dashes
      if (tableStart >= 0 && line.match(/^\|[\s\-|]+\|$/)) {
        continue; // Skip separator line
      }
      
      // Look for end of table (empty line after table rows or end indicators)
      if (tableStart >= 0 && i > tableStart + 1) {
        if (line === '' || 
            line.includes('---') && !line.includes('|') ||
            line.toLowerCase().includes('interpretive notes') ||
            line.toLowerCase().includes('conclusion')) {
          tableEnd = i;
          break;
        }
      }
    }

    if (tableStart === -1) {
      return null;
    }

    if (tableEnd === -1) {
      tableEnd = lines.length;
    }

    return lines.slice(tableStart, tableEnd).join('\n');
  }

  private parseTableRows(tableSection: string): CongressMember[] {
    const lines = tableSection.split('\n');
    const members: CongressMember[] = [];

    for (const line of lines) {
      const trimmedLine = line.trim();
      
      // Skip header, separator, and empty lines
      if (!trimmedLine || 
          trimmedLine.includes('Congress Member') ||
          trimmedLine.match(/^\|[\s\-|]+\|$/)) {
        continue;
      }

      // Parse table row
      const member = this.parseTableRow(trimmedLine);
      if (member) {
        members.push(member);
      }
    }

    return members;
  }

  private parseTableRow(row: string): CongressMember | null {
    try {
      // Split by | and clean up
      const cells = row.split('|').map(cell => cell.trim()).filter(cell => cell !== '');
      
      if (cells.length < 5) {
        return null;
      }

      const nameCell = cells[0];
      const chamberCell = cells[1];
      const stateDistrictCell = cells[2];
      const rankCell = cells[3];
      const reasonCell = cells[4];

      // Parse rank
      const rank = this.parseRank(rankCell);
      if (rank === null) {
        return null;
      }

      // Extract party from name if present (e.g., "Joe Manchin (D)" -> name: "Joe Manchin", party: "D")
      const nameInfo = this.parseNameForParty(nameCell);
      
      // Parse state/district (e.g., "MD-03" -> state: "MD", district: "03", or "TN" -> state: "TN")
      const stateInfo = this.parseStateDistrict(stateDistrictCell.trim());

      return {
        name: nameInfo.name,
        chamber: chamberCell.trim(),
        party: nameInfo.party ? this.expandParty(nameInfo.party) : undefined,
        state: stateInfo.state,
        district: stateInfo.district,
        rank: rank,
        reason: reasonCell.trim()
      };

    } catch (error) {
      console.warn('Error parsing table row:', row, error);
      return null;
    }
  }

  private parseNameForParty(nameCell: string): { name: string; party?: string } {
    try {
      // Pattern: "Joe Manchin (D)" or "John Barrasso (R)" - extract party if present
      const simplePartyMatch = nameCell.match(/^(.+?)\s*\(([RDI])\)$/);
      if (simplePartyMatch) {
        const [, name, party] = simplePartyMatch;
        return {
          name: name.trim(),
          party: party
        };
      }

      // Pattern: "John Barrasso (R-WY)" - extract party from party-state format
      const partyStateMatch = nameCell.match(/^(.+?)\s*\(([RDI])-/);
      if (partyStateMatch) {
        const [, name, party] = partyStateMatch;
        return {
          name: name.trim(),
          party: party
        };
      }

      // No party info found, return just the name
      return {
        name: nameCell.trim(),
        party: undefined
      };

    } catch (error) {
      console.warn('Error parsing name cell:', nameCell, error);
      return {
        name: nameCell.trim(),
        party: undefined
      };
    }
  }

  private parseStateDistrict(stateDistrictCell: string): { state: string; district?: string } {
    try {
      // Pattern: "MD-03" -> state: "MD", district: "03"
      const districtMatch = stateDistrictCell.match(/^([A-Z]{2})-(\d+)$/);
      if (districtMatch) {
        const [, state, district] = districtMatch;
        return {
          state: state,
          district: district
        };
      }

      // Pattern: "TN" -> state: "TN" (Senate, no district)
      const stateMatch = stateDistrictCell.match(/^([A-Z]{2})$/);
      if (stateMatch) {
        return {
          state: stateMatch[1],
          district: undefined
        };
      }

      // Fallback: return as-is
      return {
        state: stateDistrictCell,
        district: undefined
      };

    } catch (error) {
      console.warn('Error parsing state/district:', stateDistrictCell, error);
      return {
        state: stateDistrictCell,
        district: undefined
      };
    }
  }

  private parseRank(rankCell: string): number | null {
    try {
      // Extract number from rank cell
      const match = rankCell.match(/(\d+)/);
      if (!match) {
        return null;
      }
      
      const rank = parseInt(match[1], 10);
      return isNaN(rank) ? null : rank;

    } catch (error) {
      return null;
    }
  }

  private expandParty(partyCode: string): string {
    const parties: { [key: string]: string } = {
      'R': 'Republican',
      'D': 'Democrat', 
      'I': 'Independent'
    };
    return parties[partyCode] || partyCode;
  }


  private extractBillId(content: string): string | undefined {
    // Look for bill patterns like S.383-116, HR.1234-117, etc.
    const billMatch = content.match(/([SH]\.?\s*\d+[-\s]\d+)/i);
    return billMatch ? billMatch[1] : undefined;
  }

  private isInvestigationComplete(content: string): boolean {
    const completionIndicators = [
      'TERMINATE',
      'investigation complete',
      'table delivered',
      'all findings consolidated',
      'no further puzzle pieces'
    ];

    const contentLower = content.toLowerCase();
    return completionIndicators.some(indicator => 
      contentLower.includes(indicator.toLowerCase())
    );
  }
}

// Export singleton instance
export const tableParser = new TableParser();

// Helper function for easy use
export function parseCongressTable(messageContent: string): ParsedTable | null {
  return tableParser.parseOrchestratorTable(messageContent);
}